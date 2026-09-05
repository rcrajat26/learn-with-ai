---

# PART 3 — UNDER THE HOOD

PART 3 owns the mechanism underneath every pattern PART 1 named and every principle PART 2 argued
about. Its unit of work is the source walk: the class, the method, the field, the branch and the
constant that make a pattern real at runtime — JVM dispatch and inline caches, class initialisation,
proxy generation, the JDK's and Spring's own pattern implementations, records and sealed types as
pattern-retiring language features, and the runtime internals of the resilience, event-sourcing and
outbox patterns. It ends with the measurement that decides whether an indirection costs anything and
the incidents where a design decision was the documented root cause.

Where PART 1 says "a strategy is an interface with implementations", PART 3 says which bytecode the
call emits, how wide HotSpot's type profile is before it gives up, and what that costs against
`ClientRestrictions`' 30 ms p99. Nothing here is allowed to say "the JVM optimises it" without naming
the flag.

## §3.1 JVM dispatch: `invokevirtual`/`invokeinterface`, vtable/itable, monomorphic → bimorphic → megamorphic inline caches, and the measured cost of a strategy interface

3.1.1 The five invocation bytecodes and which Java construct emits each: `invokestatic` (static method),
      `invokespecial` (constructor, `private` method, `super.m()`), `invokevirtual` (instance method on
      a class type), `invokeinterface` (instance method on an interface type), `invokedynamic`
      (lambda, record `equals`/`hashCode`/`toString`, `typeSwitch`, string concat). `[API]`

3.1.2 `invokevirtual` resolves to a **vtable index** fixed at class-load time: the receiver's
      `Klass` holds a vtable whose slot for a given method is the same index in every subclass, so
      dispatch is one load of the klass pointer plus one indexed load plus an indirect jump. `[SOURCE]`

3.1.3 `invokeinterface` cannot use a fixed index, because a class implementing two interfaces has no
      single consistent slot numbering — so it searches an **itable**: the receiver's itable is scanned
      for the interface's `Klass`, then the method is fetched at the offset within that interface's
      block. Two levels of indirection plus a linear scan over implemented interfaces. `[SOURCE]`

3.1.4 The itable-scan cost is what makes interface dispatch measurably worse than class dispatch when
      it is *not* inlined; Shipilev's dispatch measurements show C1 interface cases at ~136.2 ns/op
      against ~120.5 ns/op for abstract-class cases at bias=0.5. `[NUM]` `[RESEARCH]`

3.1.5 The **inline cache** sits in front of both: HotSpot patches the call site with the observed
      receiver `Klass` and a direct branch to that klass's method, guarded by a klass compare. State
      machine: **unresolved (clean) → monomorphic → megamorphic (vtable/itable stub)**. `[SOURCE]`

3.1.6 The flag that switches the mechanism off for experiment, quoted from
      `src/hotspot/share/runtime/globals.hpp`: `product(bool, UseInlineCaches, true, "Use Inline Caches
      for virtual calls ")`. `-XX:-UseInlineCaches` degrades every virtual call to a full vtable/itable
      dispatch, which is how you measure what the cache is worth. `[SOURCE]` `[API]` `[NUM]`

3.1.7 The interpreter and C1 record receiver types into `ReceiverTypeData` in the method's
      `MethodData` (the profile), one row per observed type. `[SOURCE]`

3.1.8 `-XX:TypeProfileWidth` — **default 2**, range 0–8 — "number of receiver types to record in
      call/cast profile". It is the number of rows in `ReceiverTypeData`, and therefore the width at
      which the profile stops being useful. The value and range are from the OpenJDK HotSpot wiki's
      TypeProfile page; the declaration is in neither `runtime/globals.hpp` nor `opto/c2_globals.hpp`
      as fetched, so the **declaring file is unconfirmed** — see the notes block. `[NUM]` `[API]` `[RESEARCH]`

3.1.9 The consequence of width 2: C2 supports **monomorphic** and **bimorphic** guarded inlining, and
      **declares any call site with three or more observed receiver types megamorphic**. Three is the
      cliff, not "many". `[NUM]` `[PROVE]`

3.1.10 A **polluted profile** is the specific failure: the profile holds the first ≤ 2 types with low
       counts while the *total* count is high, which is C2's signal that `ReceiverTypeData` overflowed
       and none of the recorded types can be trusted — so it uses none of them. `[TRAP]`

3.1.11 What C2 does with a **monomorphic** strategy interface: Class Hierarchy Analysis (CHA) or the
       type profile proves one receiver, so C2 emits a klass guard and **inlines the implementation
       body**, then constant-folds, scalar-replaces and dead-code-eliminates across the former call
       boundary. The indirection disappears entirely. `[PROVE]`

3.1.12 What C2 does with a **bimorphic** site: two klass guards, both bodies inlined, an uncommon trap
       on the fall-through. Still no dispatch cost, but roughly double the inlined code and pressure
       on the inlining budget. `[NUM]`

3.1.13 What C2 does with a **megamorphic** site: no inlining at all — C2 emits a **vtable or itable
       stub** call. Nothing downstream can be optimised through it, which is the real cost: not the
       jump, the lost inlining. `[PROVE]`

3.1.14 The measured spread, stated honestly: monomorphic ~2.816 ns/op, bimorphic ~3.258 ns/op,
       megamorphic ~4.896 ns/op in the DZone/insightfullogic measurement, with the inlinable
       monomorphic case collapsing far below and the megamorphic case staying ~4.278 ns/op even when
       the target is trivially inlinable. `[NUM]` `[RESEARCH]`

3.1.15 The **uncommon trap and deoptimisation** consequence: a call site that was monomorphic for
       hours and then sees a second type traps, deoptimises, and recompiles — so a rarely-exercised
       rule implementation deployed at 09:00 costs a recompile storm on the first request that uses it.
       `[X-REF 06]` `[X-REF 25]`

3.1.16 `-XX:+PrintInlining` output shapes to recognise: `inline (hot)`, `too big`,
       `not inlineable`, `megamorphic call`, and `type profile` — the last is the direct evidence a
       site went megamorphic. `[DIAG]` `[API]`

3.1.17 The conclusion for `ClientRestrictions`: 8 instances, extreme request rate, a **30 ms p99**
       budget, and a rule-strategy interface. Even a fully megamorphic site at ~5 ns costs ~5 ns —
       0.000017% of the budget. A `List<RestrictionRule>` of 11 rule types evaluated per decision is
       ~55 ns of dispatch against 30,000,000 ns. **Dispatch is not the cost.** `[NUM]` `[PROVE]`

3.1.18 The shape where it *is* the cost, named precisely: a megamorphic call **inside a hot loop over
       19.8M `FundsLedger` entries**, where the lost inlining blocks bounds-check elimination and
       scalar replacement across millions of iterations — not one call, a billion. `[DECIDE]`

*(18 leaves)*

## §3.2 Escape analysis and scalar replacement — why a builder's allocation is often free, and when it is not

3.2.1 Escape analysis is a C2 analysis, not a GC feature. The three escape states, in the OpenJDK
      HotSpot wiki's own words: **GlobalEscape** — "an object escapes the method and thread (stored
      into a static field or stored into a field of an escaped object or returned as the result of the
      current method)"; **ArgEscape** — "an object passed as argument or referenced by argument but not
      globally escape during a call"; **NoEscape** — "a scalar replaceable object". `[SOURCE]`

3.2.2 The flag declarations, quoted from `src/hotspot/share/opto/c2_globals.hpp`:
      `product(bool, DoEscapeAnalysis, true, "Perform escape analysis")`. On by default;
      `-XX:-DoEscapeAnalysis` is the A/B switch for proving a claim in a benchmark. `[SOURCE]` `[API]` `[NUM]`

3.2.3 **Scalar replacement** is the payoff, and it is not "stack allocation" — the wiki says so
      explicitly: "C2 does NOT replace a heap allocation with a stack allocation for non globally
      escaping objects." A NoEscape object is *deleted* and its fields become SSA values in registers.
      There is no object, so there is no allocation, no header, no GC pressure, no write barrier.
      `[TRAP]` `[SOURCE]` `[PROVE]`

3.2.4 `product(bool, EliminateAllocations, true, "Use escape analysis to eliminate allocations")` — the
      scalar-replacement switch, on by default and separately disableable from the analysis itself.
      `[SOURCE]` `[API]` `[NUM]`

3.2.5 `product(intx, EliminateAllocationArraySizeLimit, 64, "Array size (number of elements) limit for
      scalar replacement")` — the hard ceiling nobody quotes: an array of more than **64** elements is
      never scalar-replaced, however provably local it is. `[SOURCE]` `[NUM]`

3.2.6 `[TRAP]` The evidence flag is not available in the JVM you ship:
      `develop(bool, PrintEliminateAllocations, false, "Print out when allocations are eliminated")` and
      `develop(bool, PrintEscapeAnalysis, false, "Print the results of escape analysis")` are
      **`develop`**, not `product` — so they exist only in a fastdebug/slowdebug build and
      `-XX:+PrintEliminateAllocations` on a release JDK is an "Unrecognized VM option" launch failure.
      On a product build the observable proxy is the allocation rate itself (`-XX:+PrintGC`, JFR
      `jdk.ObjectAllocationSample`, or async-profiler `-e alloc`). `[SOURCE]` `[DIAG]`

3.2.7 **Lock elision/coarsening** is the second payoff:
      `product(bool, EliminateLocks, true, "Coarsen locks when possible")`, which is why `StringBuffer`
      inside one method costs what `StringBuilder` costs. `[SOURCE]` `[X-REF 05]`

3.2.8 Failure condition 1 — **the object escapes a non-inlined call**. Escape analysis runs *after*
      inlining and only over what was inlined. Pass the builder to a method C2 declined to inline
      (too big, megamorphic, `@DontInline`) and it becomes ArgEscape at best. `[PROVE]`

3.2.9 Failure condition 2 — **a merge point**. If a reference is assigned in two branches
      (`var b = cond ? new Builder() : cached`), C2's allocation elimination gives up on the phi;
      the historical limitation is that scalar replacement does not survive control-flow merges of
      distinct allocations. `[RESEARCH]`

3.2.10 Failure condition 3 — **`synchronized` on the object, or `Object.hashCode()`/identity use**,
      forces a real header and therefore a real object. Identity is the thing a scalar cannot have.
      `[PROVE]`

3.2.11 Failure condition 4 — the object is **stored into a field or a collection**, or **returned**.
      `StakeReservation.Builder.build()` returning the built record makes the *record* GlobalEscape;
      the *builder* can still be NoEscape, which is exactly the case that matters. `[PROVE]`

3.2.12 Verdict on builder allocation for `StakeReservation`: at **2.8M reservations/day, 1,200/sec**,
       the builder is method-local, never synchronised, never stored — the canonical NoEscape shape,
       so the builder is genuinely free and the argument "a builder allocates, so use a telescoping
       constructor" is measuring nothing. `[PROVE]` `[NUM]`

3.2.13 Verdict on **object pooling** given the same mechanism: pooling *defeats* escape analysis by
       construction — a pooled object is reachable from the pool, therefore GlobalEscape, therefore a
       real allocation that also survives into old generation and gets traced on every cycle. Pooling
       plain heap objects is strictly worse than allocating them. `[DECIDE]` `[X-REF 06]`

3.2.14 The one case pooling still wins in QuizStakes, with the mechanism: `DocumentVerification`'s
       **2–6 MB document buffers** at 24k uploads/day → 68 GB/day. These cross the G1 humongous
       threshold, are not scalar-replaceable at any size, and their cost is region allocation and
       zeroing, not header overhead. Pool the buffer; never pool the DTO. `[NUM]` `[DECIDE]`

*(14 leaves)*

## §3.3 Class initialisation: JVMS §5.5, the init lock, and the initialization-on-demand holder idiom

3.3.1 The five triggers for initialisation (JVMS §5.5): first `new`, first `getstatic`/`putstatic` of a
      non-constant static field, first `invokestatic`, reflective initialisation
      (`Class.forName(name)` with `initialize=true`), and initialisation of a subclass. `[SOURCE]`

3.3.2 **The `static final` constant exemption is the trap**: reading a `static final` field of a
      primitive or `String` type initialised with a compile-time constant expression is resolved by
      `javac` into the constant pool of the *reading* class, so it does **not** trigger initialisation
      of the declaring class. `[TRAP]` `[SOURCE]`

3.3.3 Step 1 of §5.5: "Synchronize on the initialization lock, **LC**, for C." The spec's own note:
      **"The initialization lock is the `Class` object for C."** `[SOURCE]`

3.3.4 Step 2: if the `Class` object indicates initialisation is in progress **by some other thread**,
      release LC and **block until notified**, then go to step 11 — this is the mechanism that makes
      the holder idiom thread-safe with no `synchronized` in the source. `[SOURCE]` `[PROVE]`

3.3.5 Step 3: if initialisation is in progress **by the current thread**, this is a recursive request —
      release LC and **complete normally**. This is why a `<clinit>` cycle does not deadlock and why it
      can observe *partially initialised* state. `[SOURCE]` `[TRAP]`

3.3.6 Step 4: already complete → release LC, complete normally. This is the fast path taken on every
      call after the first, and it is not a lock acquisition in practice — HotSpot checks the klass
      init state inline and the JIT folds it away once the class is initialised. `[PROVE]`

3.3.7 Step 5: state **erroneous** → release LC and throw `NoClassDefFoundError`. The class is
      permanently unusable; a second call does **not** re-run `<clinit>`. `[SOURCE]` `[TRAP]`

3.3.8 Step 6: record "in progress by the current thread", **release LC**. The lock is held only across
      the state transition, not across `<clinit>` execution.

3.3.9 Step 7: recursively initialise the direct superclass SC; abrupt completion marks C erroneous,
      notifies waiters, and propagates the same exception. `[SOURCE]`

3.3.10 Step 8: determine enabled assertions from the defining class loader. Step 9: **execute
       `<clinit>`**. `[SOURCE]`

3.3.11 Step 10: normal completion → acquire LC, label **fully initialized**, notify all threads waiting
       on LC, release LC. The `notifyAll` on LC is what releases the threads parked in step 2.
       `[SOURCE]`

3.3.12 Step 11: `<clinit>` threw E. If E is not an `Error`, wrap it in `ExceptionInInitializerError`
       with E as the cause (or substitute an `OutOfMemoryError` if the wrapper cannot be allocated);
       mark erroneous, notify, rethrow. Step 12: acquire LC, release LC. `[SOURCE]`

3.3.13 The holder idiom, mechanism stated end to end: `Holder` is a distinct class, so its
       initialisation is deferred to the **first `getstatic Holder.INSTANCE`** — laziness from the class
       loader — and the JVM's own §5.5 procedure supplies mutual exclusion, publication and
       happens-before. Zero synchronisation appears in the source because the synchronisation is the
       spec's. `[PROVE]` `[SOURCE]`

3.3.14 Why it beats DCL concretely: the guard the JIT emits after initialisation is *nothing* — the
       klass-init check is constant-folded — whereas DCL keeps a `volatile` read on the fast path
       forever. `[PROVE]` `[X-REF 06]`

*(14 leaves)*

## §3.4 `volatile`, safe publication, final-field semantics, and why DCL needs the barrier

3.4.1 `instance = new RateTable()` is three operations at bytecode level — `new` (allocate,
      header written, fields zeroed), `invokespecial <init>` (constructor writes), `putstatic`
      (publish) — and the JMM permits the third to be observed before the second by another thread.
      `[PROVE]` `[SOURCE]`

3.4.2 The **partially-constructed-object publication hazard** stated exactly: thread B's
      unsynchronised read can see a **non-null reference** whose `final` fields still read as their
      default values (`0`, `null`, `false`). Not a torn object — a fully-typed object with default
      fields. `[TRAP]`

3.4.3 JLS §17.4.4: a `volatile` **write** and a subsequent `volatile` **read of the same variable**
      form a synchronizes-with edge, hence a happens-before edge. That edge is the entire fix. `[SOURCE]`

3.4.4 The release/acquire reading: the `volatile` write is a **release** (all prior writes are visible
      to anyone who acquires), the `volatile` read is an **acquire** (nothing after it may be hoisted
      above it). `[X-REF 05]`

3.4.5 The hardware realisation on x86-64: the `volatile` store compiles to a plain `mov` followed by a
      `lock addl $0,(%rsp)` (a full StoreLoad fence); the `volatile` load is a plain `mov` because x86
      is already TSO. So on x86 the *read* side is free and the *write* side is not. `[NUM]` `[RESEARCH]`

3.4.6 **Why DCL without `volatile` appears to work** — the reason it survives code review and testing:
      on x86-64 with TSO the reordering that breaks it is a *compiler* reordering, not a hardware one,
      and it requires the constructor's stores to be sunk past the publish, which C2 only does under
      specific inlining shapes. It works in every test and fails once, in production, on one
      architecture or after one JIT decision changes. `[TRAP]` `[PROVE]`

3.4.7 The second, subtler failure with a non-`volatile` field: the first check can read `null` on the
      fast path even after another thread published, so the lock is taken again — a correctness-neutral
      but performance-relevant staleness. `[PROVE]`

3.4.8 `[TRAP]` The "DCL is fixed by making the *object's* fields `final`" claim. Final-field freeze
      helps *only* if the reference itself is safely published; a racy read of the reference is outside
      the freeze's guarantee.

3.4.9 JLS **§17.5** final-field semantics: there is a **freeze** action at the end of the constructor,
      and a thread that reads a reference written after the freeze is guaranteed to see the correctly
      initialised `final` fields — **provided** it did not obtain the reference through a race.
      `[SOURCE]`

3.4.10 §17.5's **`this`-escape** exclusion: publishing `this` from inside the constructor (registering
       a listener, starting a thread, passing `this` to a collaborator) voids the freeze guarantee for
       every reader that got the reference that way. `[TRAP]`

3.4.11 The five safe-publication idioms, named: static initialiser (§3.3's holder), `volatile` or
       `AtomicReference` field, `final` field of a properly constructed object, a field guarded by a
       lock held by both writer and reader, and a `java.util.concurrent` collection.
       `[TABLE]` `[X-REF 05]`

3.4.12 `record` and the freeze: a record's components are `final`, so a record published through any of
       the five idioms is safe; a record published through a racy non-`volatile` field is **not**, and
       "records are immutable so they're thread-safe" is the same DCL error one level up. `[TRAP]`

3.4.13 Enum singletons and DCL are the *same* mechanism: `enum` constants are `static final` fields
       initialised in `<clinit>`, so §3.3's init lock does the publication. There is nothing to get
       wrong. `[PROVE]`

3.4.14 The `SELF_EXCLUDED` restriction as the QuizStakes stake: a **hard 500 ms** effectiveness budget
       on a regulatory control means the restriction set must be safely published to the reading thread
       or the system can serve a stake to a self-excluded client. This is the one place in the domain
       where a publication race is a regulatory breach, not a latency blip. `[NUM]` `[SAY]`

3.4.15 `[VERSION-TRAP]` "Java 5 fixed `volatile`, so DCL is now fine" — true and misleading. JSR-133
       made DCL *correct with* `volatile`; it did not make the `volatile` optional, and pre-JSR-133
       advice that DCL is unfixable is equally stale.

3.4.16 `[SAY]` "DCL is correct with `volatile` and broken without it, but I'd still write the holder
       idiom — the JVM's class-init lock gives me the same laziness and publication with no
       synchronisation on the fast path and six fewer lines to get wrong."

*(16 leaves)*

## §3.5 Enum singleton: the serialization mechanism, `readResolve`, and the reflection guard

3.5.1 `Enum` implements `Serializable`, but its serialized form is **special-cased**: an enum constant
      is written as its **name** only, not its fields. `ObjectOutputStream.writeEnum` emits
      `TC_ENUM`, the class descriptor, and the result of `name()`. `[SOURCE]` `[API]`

3.5.2 `ObjectInputStream.readEnum` resolves the constant with `Enum.valueOf(clazz, name)` — it never
      allocates. Deserialisation therefore *cannot* produce a second instance; it returns the
      canonical constant or throws. `[SOURCE]` `[PROVE]`

3.5.3 The consequence that makes enum-as-singleton airtight: `Enum` declares `clone()` to throw
      `CloneNotSupportedException`, and its `writeObject`/`readObject`/`writeReplace`/`readResolve`
      are `private final` no-ops that throw `InvalidObjectException` — the JDK closes every hole
      rather than documenting it. `[SOURCE]` `[RESEARCH]`

3.5.4 Enum fields are **not serialized**, which is the cost nobody states: a mutable field on an enum
      singleton is silently not round-tripped. `[TRAP]`

3.5.5 `[TRAP]` `Enum.valueOf` throwing `IllegalArgumentException` on an unknown name is how a renamed
      constant becomes an unreadable message three years later — the enum's serialized form is its
      *name*, so renaming a constant is a wire-format breaking change. Directly relevant to the
      `AO-`/`AA-` status vocabulary.

3.5.6 For a **non-enum** singleton, `readObject` allocates a fresh instance without running the
      constructor, breaking the invariant. The fix is `private Object readResolve() { return INSTANCE; }`
      — invoked by `ObjectInputStream` after the object graph is read, its return value replacing the
      deserialized instance. `[API]` `[SOURCE]`

3.5.7 `readResolve` mechanics that matter: it must be declared `readResolve` exactly, may be `private`
      (found reflectively), and must return `Object`. A `private readResolve` is **not** inherited by
      subclasses — for an inheritable class it must be at least package-private. `[API]` `[TRAP]`

3.5.8 The second half of the `readResolve` fix, always omitted: every non-`transient` field of a
      `readResolve`-protected singleton must be `transient`, or a **stolen-reference attack** can
      extract the field's value from the discarded instance before `readResolve` replaces it.
      `[TRAP]` `[SOURCE]`

3.5.9 The reflection attack on a non-enum singleton:
      `var c = RateTable.class.getDeclaredConstructor(); c.setAccessible(true); c.newInstance();`
      — the private constructor runs and a second instance exists. The only in-language defence is a
      constructor guard that throws on second invocation. `[BUILD]` `[TRAP]`

3.5.10 The **reflection guard that makes enums immune**, named exactly:
       `Constructor.newInstance` tests `(clazz.getModifiers() & Modifier.ENUM) != 0` and throws
       `IllegalArgumentException("Cannot reflectively create enum objects")`. It is a check in the
       reflection layer, not a language rule. `[SOURCE]` `[API]`

3.5.11 The known bypass, stated so the claim is honest: obtaining the internal `ConstructorAccessor`
       reflectively sidesteps the `Modifier.ENUM` check. "Reflection-proof" means "proof against
       `Constructor.newInstance`", and under JPMS strong encapsulation the bypass now needs
       `--add-opens java.base/java.lang.reflect=ALL-UNNAMED`. `[RESEARCH]` `[VERSION-TRAP]`

3.5.12 Bloch, *Effective Java* item 3: "a single-element enum type is often the best way to implement a
       singleton." The stated limitation: an enum singleton cannot extend a class other than `Enum`.
       `[SOURCE]` `[DECIDE]`

*(12 leaves)*

## §3.6 `Cloneable`/`clone()` source walk, and copy-constructor/copy-factory alternatives

3.6.1 `Object.clone` is declared `protected native Object clone() throws CloneNotSupportedException`
      — `native`, so there is no Java source to read; the VM allocates an object of the same class and
      copies the instance fields bitwise. `[SOURCE]` `[API]`

3.6.2 `Cloneable` is `public interface Cloneable {}` — **empty**. It declares no `clone` method. It is
      a marker whose sole runtime effect is to change `Object.clone`'s behaviour from throwing to
      copying. `[SOURCE]` `[TRAP]`

3.6.3 The interface therefore inverts the normal contract: implementing `Cloneable` modifies the
      behaviour of a `protected` method on the **superclass**, which Bloch calls "extralinguistic".
      `[SOURCE]`

3.6.4 `CloneNotSupportedException` is a **checked** exception thrown by `Object.clone` when the class
      does not implement `Cloneable` — so every `clone()` override must either catch an exception that
      provably cannot happen or redeclare it. Boilerplate with no information content. `[TRAP]`

3.6.5 `clone` **bypasses constructors**: no compact-constructor validation, no `final`-field
      assignment, no invariant establishment. A `StakeReservation` whose constructor guarantees
      `bonusLeg + cashLeg == total` gets no such guarantee from `clone`. `[PROVE]`

3.6.6 `ArrayList.clone` source walk: it calls `super.clone()`, then
      `v.elementData = Arrays.copyOf(elementData, size)` and `v.modCount = 0`. So the *array* is
      copied but the **elements are the same references** — a textbook one-level-deep copy that reads
      as deep because a new array appeared. `[SOURCE]` `[TRAP]`

3.6.7 `HashMap.clone` and `TreeMap.clone` are the same shape: new table/nodes, shared keys and values.
      `Arrays.copyOf` and `System.arraycopy` are shallow by definition. `[SOURCE]`

3.6.8 The shallow/deep taxonomy as three levels, not two: **reference copy** (`b = a`), **shallow copy**
      (new object, shared referents), **deep copy** (new object, recursively new referents) — plus the
      practical fourth, **shallow copy of an immutable graph**, which is deep enough and costs nothing.
      `[TABLE]`

3.6.9 `clone` and `final` fields are incompatible: `clone` cannot assign a `final` field, so a class
      with a `final` mutable field cannot deep-copy it in `clone` at all. This is a hard language-level
      block, not a style preference. `[PROVE]`

3.6.10 Arrays are the one place `clone` is idiomatic and correct: `int[] copy = original.clone()` is
       typed, fast, and has no invariant to break. Bloch: "arrays are the sole compelling use of the
       clone facility." `[SOURCE]` `[DECIDE]`

3.6.11 The Bloch alternative (*Effective Java* item 13): a **copy constructor**
      (`public StakeReservation(StakeReservation other)`) or a **copy factory**
      (`static StakeReservation copyOf(StakeReservation other)`). Advantages named: no `Cloneable`, no
      checked exception, no `final`-field problem, constructors run so invariants hold, and the
      parameter type can be an **interface** — `new ArrayList<>(someCollection)`, `Map.copyOf`,
      `List.copyOf`, `EnumSet.copyOf`. `[SOURCE]` `[API]`

3.6.12 The record idiom that replaces prototype entirely: a `withX` method returning a new record via
       the canonical constructor, plus `Map.copyOf`/`List.copyOf` in the compact constructor to close
       the shallow-immutability gap (see §3.12.13). `[BUILD]`

*(12 leaves)*

## §3.7 JDK dynamic proxy internals: `Proxy.newProxyInstance`, the generated class, caching, `equals`/`hashCode`/`toString`, default methods

3.7.1 `public static Object newProxyInstance(ClassLoader loader, Class<?>[] interfaces,
      InvocationHandler h)` — the whole public surface. It resolves (or generates) the proxy class,
      then invokes its single constructor `$Proxy0(InvocationHandler)`. `[API]` `[SOURCE]`

3.7.2 `public static Class<?> getProxyClass(ClassLoader loader, Class<?>... interfaces)` — **deprecated**
      in current JDKs in favour of `newProxyInstance`, because a proxy class obtained separately can be
      instantiated in ways that bypass the intended access checks. `[API]` `[VERSION-TRAP]`

3.7.3 The **proxy class cache**: "if a proxy class for the same permutation of interfaces has already
      been defined by the class loader, then the existing proxy class will be returned." Keyed by
      (class loader, ordered interface list) — the cache is `Proxy.proxyClassCache`, a
      `WeakCache<ClassLoader, Class<?>[], Class<?>>`. `[SOURCE]` `[API]` `[RESEARCH]`

3.7.4 Class-name reservation: "class names beginning with `$Proxy` are reserved for proxy classes."
      `$Proxy0`, `$Proxy1`, … numbered per definition, not per interface. `[SOURCE]`

3.7.5 Generated class shape: `final class $Proxy0 extends java.lang.reflect.Proxy implements
      <your interfaces>`. Extending `Proxy` consumes the single inheritance slot — **which is the
      mechanism-level reason a JDK proxy can never proxy a class**. `[PROVE]` `[DIAG]`

3.7.6 The generated body: one `private static final java.lang.reflect.Method` field per proxied method,
      initialised in `<clinit>` via `Class.forName(...).getMethod(...)`, so the `Method` lookup is paid
      once at class-init rather than per call. `[SOURCE]` `[DIAG]`

3.7.7 The `m0`–`m3` naming convention: `m0` = `hashCode`, `m1` = `equals`, `m2` = `toString`, then
      interface methods from `m3` upward in declaration order. This is `ProxyGenerator`'s emission
      order, not a specified contract — do not build on it, but recognise it in a decompiled proxy.
      `[RESEARCH]` `[DIAG]`

3.7.8 Each generated method body is the same four lines: load `super.h`, load `this`, load the static
      `Method`, box the arguments into an `Object[]`, `invokeinterface InvocationHandler.invoke`,
      unbox/cast the result. The **boxing of every primitive argument** is the per-call cost. `[NUM]`

3.7.9 `equals`, `hashCode` and `toString` are **routed to the handler** — the javadoc: they are
      "encoded and dispatched to the invocation handler's `invoke` method", with the `Method` object's
      **declaring class being `java.lang.Object`**, and they "logically precede all proxy interfaces".
      `[SOURCE]` `[API]`

3.7.10 `[TRAP]` The consequence: a handler that does not special-case `equals`/`hashCode`/`toString`
       forwards them to the target, so `proxy.equals(proxy)` may be `false` and the proxy is unusable
       as a `HashMap` key. Symptom: a bean vanishing from a `Set`. Fix: handle the three
       `Object` methods before delegating.

3.7.11 The remaining `Object` methods — `getClass`, `notify`, `notifyAll`, `wait`, and `clone`/`finalize`
       — are **not** intercepted: `getClass` is `final`, so `proxy.getClass()` returns `$Proxy0`, never
       the target's class. `[TRAP]`

3.7.12 Method resolution across duplicate interfaces: when two proxied interfaces declare the same
       name and parameter signature, **interface order becomes significant** and the `Method` passed is
       from the **foremost** interface in the list, "regardless of the reference type through which it
       was invoked". `[SOURCE]` `[TRAP]`

3.7.13 **Default methods**: a proxy overrides them like any other interface method, so an
       `InvocationHandler` intercepts them too — the default body does **not** run unless the handler
       invokes it. `[TRAP]` `[API]`

3.7.14 Invoking the default body from a handler is `InvocationHandler.invokeDefault(proxy, method,
       args)` — **added in JDK 16**. Before that it required a `MethodHandles.Lookup`
       `findSpecial`/`unreflectSpecial` dance with `--add-opens`. `[VERSION-TRAP]` `[API]`

3.7.15 `Proxy.isProxyClass(Class<?>)` and `Proxy.getInvocationHandler(Object)` (throws
       `IllegalArgumentException` for a non-proxy) — the only supported introspection. Spring's
       `AopUtils.isJdkDynamicProxy` is a thin wrapper. `[API]`

3.7.16 JDK 9+ module and package placement, as four rules: all interfaces public and in
       exported/open packages → proxy is **public** in an unspecified unconditionally-exported non-open
       package; any non-public interface → proxy is **non-public in that interface's package and
       module** (and all non-public interfaces must share one); any interface in a non-exported package
       → the proxy lands in a non-exported non-open package of a **dynamic module**. The pre-9
       `com.sun.proxy.$Proxy0` name is therefore no longer universal. `[SOURCE]` `[VERSION-TRAP]` `[TABLE]`

*(16 leaves)*

## §3.8 Subclass proxying: CGLIB/ByteBuddy, Spring's proxy-vs-target-class decision, the interceptor chain, and the self-invocation bypass

3.8.1 CGLIB generates a **subclass** of the target at runtime and overrides each non-`final` method.
      Since Spring 3.2 it is **repackaged inside `spring-core`** as
      `org.springframework.cglib.*` — there is no separate `cglib` dependency to add, and the classic
      "add cglib to the pom" advice is stale. `[VERSION-TRAP]` `[API]`

3.8.2 The generated subclass name shape: `Target$$SpringCGLIB$$0` in Spring 6.x (it was
      `Target$$EnhancerBySpringCGLIB$$<hash>` in 5.x) — recognising it in a stack trace or a
      `getClass().getName()` log line is the diagnostic skill. `[DIAG]` `[VERSION-TRAP]`

3.8.3 **Byte Buddy** is the alternative bytecode generator (Mockito's engine, Hibernate's
      bytecode provider); Spring Framework itself uses its own repackaged CGLIB, not Byte Buddy.
      Getting this attribution right matters because "Spring uses Byte Buddy" is a common wrong answer.
      `[TRAP]` `[RESEARCH]`

3.8.4 `DefaultAopProxyFactory.createAopProxy(AdvisedSupport)` is the decision point, and the branch is
      readable in one sentence: if `config.isOptimize() || config.isProxyTargetClass() ||
      hasNoUserSuppliedProxyInterfaces(config)`, then — unless the target class is itself an
      **interface**, a **proxy class**, or a **lambda class** — return `new ObjenesisCglibAopProxy(config)`;
      otherwise return `new JdkDynamicAopProxy(config)`. `[SOURCE]` `[FLOW]` `[API]`

3.8.5 The three escape hatches in that branch, each with its reason: target is an interface → a JDK
      proxy is the only sane choice; target is already a `$Proxy` → subclassing a proxy is pointless;
      target is a **lambda class** (hidden class, JDK 15+) → CGLIB cannot subclass it. `[SOURCE]`

3.8.6 `ObjenesisCglibAopProxy` uses **Objenesis** to instantiate the generated subclass **without
      calling any constructor**, which is why a CGLIB-proxied bean's field initialisers and constructor
      side effects do not run on the proxy instance — and why reading a field through the proxy
      reference returns `null`. `[PROVE]` `[TRAP]`

3.8.7 `[TRAP]` The field-access corollary: `proxy.someField` is `null` even though
      `proxy.getSomeField()` works, because the field lives on the *target*, not the subclass. Every
      "my `@Value` field is null in one place" bug of this shape is this mechanism.

3.8.8 Boot's default, confirmed against `AopAutoConfiguration` at the **v3.5.0** tag: the CGLIB branch
      is `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", matchIfMissing = true)`
      carrying `@EnableAspectJAutoProxy(proxyTargetClass = true)`, and the JDK-proxy branch is
      `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", havingValue = false)`.
      The whole class sits behind `@ConditionalOnBooleanProperty(name = "spring.aop.auto",
      matchIfMissing = true)`. So **`spring.aop.proxy-target-class` is effectively `true` when absent**
      and Boot applications get CGLIB proxies unless told otherwise — the opposite of plain Spring
      Framework's historical interface-first default. `[SOURCE]` `[NUM]` `[API]` `[VERSION-TRAP]`

3.8.9 `[VERSION-TRAP]` The condition annotation itself changed: Boot **3.4** introduced
       `@ConditionalOnBooleanProperty`, and `AopAutoConfiguration` uses it at 3.5.x. Older sources
       (and older Boot) show `@ConditionalOnProperty(prefix = "spring.aop", name =
       "proxy-target-class", havingValue = "true", matchIfMissing = true)`. Same effective default,
       different annotation — do not "correct" one to the other. `[API]`

3.8.10 `@EnableAspectJAutoProxy(proxyTargetClass = true)` and
      `@EnableTransactionManagement(proxyTargetClass = true)` as the per-concern overrides. `[API]`

3.8.11 `[TRAP]` The failure the default prevents: with a JDK proxy, injecting the **concrete class**
       (`@Autowired OrderService` where `OrderService` is a class implementing `OrderPort`) fails at
       startup with "bean is expected to be of type X but was actually of type `com.sun.proxy.$Proxy42`"
       — a `BeanNotOfRequiredTypeException`, not a `ClassCastException`. `[DIAG]`

3.8.12 `ReflectiveMethodInvocation implements ProxyMethodInvocation` is the chain driver. Its state:
       `List<?> interceptorsAndDynamicMethodMatchers` and `int currentInterceptorIndex` (initialised to
       `-1`). `[SOURCE]` `[API]`

3.8.13 `ReflectiveMethodInvocation.proceed()` walks it: if
       `currentInterceptorIndex == interceptorsAndDynamicMethodMatchers.size() - 1`, call
       `invokeJoinpoint()` (reflective call on the target); otherwise take
       `++currentInterceptorIndex` and call `interceptor.invoke(this)`. Each `MethodInterceptor` calls
       `invocation.proceed()` to continue. `[SOURCE]` `[FLOW]`

3.8.14 That shape is **chain of responsibility with an index instead of a linked list** — the same
       mechanism as `ApplicationFilterChain`'s `pos` counter (§3.11.2). Naming the shared shape is the
       senior-level observation. `[X-REF 07]`

3.8.15 `MethodInterceptor extends Interceptor extends Advice` (AOP Alliance types
       `org.aopalliance.intercept.*`) — Spring reuses a 2003 standard interface rather than defining
       its own. `[API]`

3.8.16 The worked example: `TransactionInterceptor extends TransactionAspectSupport implements
       MethodInterceptor`. Its `invoke` calls `invokeWithinTransaction(...)`, which resolves the
       `TransactionAttribute`, calls `createTransactionIfNecessary`, invokes `proceed()` inside a
       try/catch, then `completeTransactionAfterThrowing` or `commitTransactionAfterReturning`.
       `@Transactional` is that method, and nothing else. `[SOURCE]` `[FLOW]` `[API]`

3.8.17 Advice ordering is by `Ordered`/`@Order`; the constants that matter:
       `Ordered.LOWEST_PRECEDENCE = Integer.MAX_VALUE` and `Ordered.HIGHEST_PRECEDENCE =
       Integer.MIN_VALUE`. `TransactionInterceptor` sits at `LOWEST_PRECEDENCE` by default, so a
       custom aspect at default order runs **outside** the transaction. `[NUM]` `[API]` `[TRAP]`

3.8.18 What subclass proxying **cannot intercept**, each with the mechanism: `final` methods (cannot be
       overridden), `private` methods (not virtual — the subclass's override is a different method),
       `static` methods (no receiver), constructors (Objenesis skips them), and `final` **classes**
       (cannot be subclassed at all — startup failure, not a silent degradation). `[TABLE]` `[PROVE]`

3.8.19 What **neither** proxy kind sees: **self-invocation**. Interception happens on the call *through
       the proxy reference*; `this.settle(...)` inside the target compiles to `invokevirtual` on the raw
       target, so the interceptor chain is never entered. It does not error — the concern is silently
       absent. `[TRAP]` `[PROVE]`

3.8.20 The full silent-failure list for the QuizStakes services: `@Transactional`, `@Cacheable`,
       `@Async`, `@Retryable`, `@PreAuthorize`, `@Timed`, and every custom `@Around` aspect. A
       `FundsLedger` method that self-calls its own `@Transactional` posting method writes ledger
       entries **outside a transaction**. `[INCIDENT]` `[NUM]`

3.8.21 `AopContext.currentProxy()` returns the proxy from a `ThreadLocal`, and requires
       `@EnableAspectJAutoProxy(exposeProxy = true)`; without it, `IllegalStateException("Cannot find
       current proxy: Set 'exposeProxy' property on Advised to 'true' to make it available")`.
       `[API]` `[DIAG]` `[SMELL]`

3.8.22 Self-injection as the other workaround: `@Autowired @Lazy private LedgerService self;` (the
       `@Lazy` is required to break the constructor cycle) — one field of pure coupling to the proxy
       mechanism, and a smell for the same reason `AopContext` is. The correct move is to extract the
       inner method to a second bean so the call crosses a proxy boundary. `[SMELL]` `[DECIDE]`

3.8.23 **AspectJ weaving as the real fix**: load-time weaving (`-javaagent:aspectjweaver.jar` +
       `@EnableLoadTimeWeaving` + `META-INF/aop.xml`) or compile-time weaving rewrites the target's own
       bytecode, so interception is inside the method and self-invocation, `final` and `private` all
       work. Cost: a build/agent step, harder debugging, and a second AOP model in the project.
       `[DECIDE]` `[X-REF 07]`

*(23 leaves)*

## §3.9 Spring's own pattern implementations, source-walked

3.9.1 `BeanFactory` (interface) / `AbstractBeanFactory` (abstract class) — **abstract factory** at the
      interface and **template method** at the class: `getBean(String)` → `doGetBean(...)` which
      handles alias resolution, the singleton cache, and the parent-factory fallback, then delegates the
      actual instantiation to the abstract `createBean(String, RootBeanDefinition, Object[])`,
      implemented by `AbstractAutowireCapableBeanFactory`. The skeleton is fixed; the creation step is
      the hook. `[SOURCE]` `[API]`

3.9.2 `DefaultSingletonBeanRegistry.getSingleton(String, ObjectFactory<?>)` and its three maps —
      `singletonObjects`, `earlySingletonObjects`, `singletonFactories` — are the **registry** pattern
      plus the circular-dependency escape hatch. `[SOURCE]` `[X-REF 07]`

3.9.3 `FactoryBean<T>` — the **factory method** pattern surfaced *as a bean*: `getObject()`,
      `getObjectType()`, `isSingleton()`. Registering a `FactoryBean` under name `x` makes `getBean("x")`
      return `getObject()` and `getBean("&x")` return the factory itself; `BeanFactory.FACTORY_BEAN_PREFIX
      = "&"`. `[API]` `[SOURCE]` `[NUM]`

3.9.4 `ObjectProvider<T>` (extends `ObjectFactory<T>`) — deferred and optional lookup:
      `getIfAvailable()`, `getIfUnique()`, `stream()`, `orderedStream()`. This is the type that makes
      per-request strategy selection possible without a hand-rolled factory, and it is the answer to
      §1.9's "when does DI make a factory redundant". `[API]` `[DECIDE]`

3.9.5 `BeanPostProcessor` — a **chain of decorators over bean instances**:
      `postProcessBeforeInitialization` and `postProcessAfterInitialization`, the latter being where
      `AbstractAutoProxyCreator` **returns a proxy instead of the bean**. Every proxy in a Spring app
      is created by a `BeanPostProcessor` returning a different object than it was given. `[SOURCE]`
      `[PROVE]`

3.9.6 `BeanFactoryPostProcessor` vs `BeanDefinitionRegistryPostProcessor` — the same chain one phase
      earlier, operating on **definitions** rather than instances;
      `ConfigurationClassPostProcessor` (which processes `@Configuration`) and
      `PropertySourcesPlaceholderConfigurer` are the two that matter. `[API]`

3.9.7 `ApplicationEventMulticaster` (interface) / `SimpleApplicationEventMulticaster` (implementation) —
      **observer**. `addApplicationListener`, `removeApplicationListener`, `multicastEvent`. Full
      internals in §3.19. `[API]`

3.9.8 `AbstractApplicationEventMulticaster`'s `ListenerRetriever` cache, keyed by
      (event type, source type) — the observer pattern with a memoised subscriber lookup, because
      resolving `ApplicationListener<T>`'s generic type per publish would be prohibitive. `[SOURCE]`

3.9.9 `JdbcTemplate` — **template method + callback**: `execute(ConnectionCallback<T>)` owns
      acquire/release/translate-exception, and the varying step is the callback
      (`StatementCallback`, `PreparedStatementCallback`, `RowMapper`, `ResultSetExtractor`). The
      inversion is the point: the template controls the resource lifecycle so the caller cannot leak it.
      `[SOURCE]` `[API]`

3.9.10 `TransactionTemplate.execute(TransactionCallback<T>)` — the same shape for transactions, and the
       **programmatic alternative to `@Transactional`** that is immune to self-invocation (§3.8.19).
       Naming this as the escape hatch is a strong answer. `[API]` `[DECIDE]`

3.9.11 `RestClient` (Spring 6.1+) / `WebClient` / the deprecated `RestTemplate` — template method with
       a fluent builder; `ClientHttpRequestInterceptor` and `ExchangeFilterFunction` are the
       **decorator/chain** seams where retry, tracing and auth headers attach. `[API]` `[VERSION-TRAP]`

3.9.12 `SQLExceptionTranslator` / `SQLErrorCodeSQLExceptionTranslator` — **strategy**, converting a
       vendor `SQLException` into Spring's `DataAccessException` hierarchy. This is also an
       **anti-corruption layer** in DDD vocabulary: one type system translated into another at the
       boundary. `[API]`

3.9.13 `HandlerMapping` (strategy: URL → handler) and `HandlerAdapter` (**adapter**: an arbitrary
       handler object invoked through a uniform interface). `RequestMappingHandlerMapping` +
       `RequestMappingHandlerAdapter` are the `@Controller` pair; `DispatcherServlet.doDispatch` is the
       algorithm that composes them. `[SOURCE]` `[API]`

3.9.14 `HandlerInterceptor` (`preHandle`/`postHandle`/`afterCompletion`) vs `Filter` — the same
       chain-of-responsibility shape at two different layers, which is why "should this be a filter or
       an interceptor" is a boundary question, not a taste question. `[DECIDE]` `[X-REF 13]`

3.9.15 `HandlerMethodArgumentResolver` and `HttpMessageConverter` — **chain of strategies** selected by
       `supportsParameter`/`canRead`; `MappingJackson2HttpMessageConverter` is one link, not the
       mechanism. `[API]`

3.9.16 `Resource` / `ResourceLoader` — **strategy over location syntax**: `ClassPathResource`,
       `FileSystemResource`, `UrlResource`, `ByteArrayResource`, selected by prefix
       (`classpath:`, `file:`, `http:`) in `DefaultResourceLoader.getResource`. `[API]` `[SOURCE]`

3.9.17 `PlatformTransactionManager` — **strategy**: `getTransaction(TransactionDefinition)`, `commit`,
       `rollback`, with `DataSourceTransactionManager`, `JpaTransactionManager` and
       `JtaTransactionManager` as the implementations. `AbstractPlatformTransactionManager` is again
       template method: propagation and synchronisation live in the base, `doBegin`/`doCommit`/
       `doRollback` are the hooks. `[API]` `[SOURCE]`

3.9.18 `Environment` / `PropertySource` / `MutablePropertySources` — **composite + chain of
       responsibility**: `getProperty` walks the ordered `PropertySource` list and returns the first
       hit, which *is* Boot's documented property-precedence order. `[SOURCE]` `[API]`

3.9.19 `ConversionService` / `GenericConversionService` / `Converter<S,T>` /
       `ConverterRegistry` — **registry + strategy** with a `Map<ConvertiblePair, GenericConverter>`
       lookup and a converter cache. `Formatter` and `ConversionService` together replace the
       `PropertyEditor` model. `[API]` `[VERSION-TRAP]`

3.9.20 `@Conditional` / `Condition.matches(ConditionContext, AnnotatedTypeMetadata)` — the
       **specification** pattern, with `@ConditionalOnClass`, `@ConditionalOnMissingBean`,
       `@ConditionalOnProperty` as composable specifications and `AnyNestedCondition`/`AllNestedConditions`
       as the combinators. Boot's entire auto-configuration is specification evaluation at startup.
       `[API]` `[SOURCE]`

*(20 leaves)*

## §3.10 The JDK's own pattern implementations, source-walked

3.10.1 `Collections.unmodifiableList(List<T>)` returns `UnmodifiableList extends UnmodifiableCollection`
       — a **decorator** that forwards every read and throws `UnsupportedOperationException` from every
       mutator. `[SOURCE]` `[API]`

3.10.2 `[TRAP]` It is a **view, not a copy**: the wrapper holds `final Collection<? extends E> c`, so
       mutating the *original* list changes what the "unmodifiable" view reports. `List.copyOf` /
       `List.of` are the actual immutable forms. The distinction between *unmodifiable* and *immutable*
       is exactly this field.

3.10.3 The same decorator, the same LSP hole (§2.8): every mutator on the shared `List` interface is a
       method the decorator cannot honour — the JDK's own canonical LSP violation, shipped
       deliberately. `[PROVE]`

3.10.4 The `java.io` **decorator stack**, source-walked: `FilterInputStream` holds
       `protected volatile InputStream in` and forwards; `BufferedInputStream` adds `byte[] buf` with
       `DEFAULT_BUFFER_SIZE = 8192`; `DataInputStream` adds typed reads; `GZIPInputStream` adds
       inflation. `new DataInputStream(new BufferedInputStream(new FileInputStream(f)))` is three
       decorators and the reason the stack order matters. `[SOURCE]` `[NUM]`

3.10.5 `[TRAP]` The decorator-order bug in the same stack: buffering *outside* the decompressor and
       buffering *inside* it are different performance profiles, and forgetting `close()` on the
       outermost wrapper loses buffered bytes. Try-with-resources on the outermost only is correct
       because `close` cascades.

3.10.6 `Integer.valueOf(int)` — **flyweight**: `if (i >= IntegerCache.low && i <= IntegerCache.high)
       return IntegerCache.cache[i + (-IntegerCache.low)];` with `low = -128` and `high = 127` by
       default. `[SOURCE]` `[NUM]`

3.10.7 `-XX:AutoBoxCacheMax=<n>` (read by `IntegerCache`'s `<clinit>` from the internal property
       `java.lang.Integer.IntegerCache.high`) raises the upper bound only. The lower bound `-128` is
       **not** configurable. `[NUM]` `[API]` `[TRAP]`

3.10.8 `Boolean.valueOf` returns `TRUE`/`FALSE`; `Character.valueOf` caches `0..127`;
       `Byte`/`Short`/`Long` cache `-128..127`; `Float` and `Double` cache **nothing**. So
       `Double.valueOf(1.0) == Double.valueOf(1.0)` is always `false`. `[NUM]` `[TABLE]`

3.10.9 `String` interning: compile-time constant expressions are interned by `javac` into the class
       file's constant pool and resolved to the pool instance; `new String("x")` is a distinct object;
       `String.intern()` is a **native** method backed by the VM's `StringTable` (a hash table sized by
       `-XX:StringTableSize`, moved from PermGen to native memory in JDK 7/8). `[SOURCE]` `[VERSION-TRAP]`

3.10.10 `AbstractList` and `modCount` — the **iterator** pattern plus its fail-fast contract:
        `Itr.checkForComodification()` compares `modCount != expectedModCount` and throws
        `ConcurrentModificationException`. `modCount` is a plain `int`, not `volatile`, which is why
        fail-fast is documented as **best-effort** and is a bug detector, not a thread-safety
        mechanism. `[SOURCE]` `[TRAP]`

3.10.11 `AbstractList.iterator()` returning a private inner `Itr` is the textbook iterator; the
        template-method half is `AbstractList` implementing every `List` method in terms of abstract
        `get(int)`/`size()`. `[SOURCE]`

3.10.12 `Comparator` **combinators**: `comparing`, `thenComparing`, `reversed`, `nullsFirst`,
        `nullsLast`, `comparingInt`. Each returns a new `Comparator` wrapping the previous one — a
        decorator chain built by `default` methods, which is what made `Comparator` extensible without
        breaking implementors (§2.9). `[API]` `[SOURCE]`

3.10.13 `ServiceLoader<S>` — **provider/service-locator** with a **lazy iterator**:
        `ServiceLoader.load(Class<S>)`, `iterator()`, `stream()` (returning
        `Stream<Provider<S>>` so a provider's type can be inspected before instantiation), and
        `reload()`. Providers are discovered from `META-INF/services/<fqn>` files or, since JDK 9,
        `provides ... with ...` in `module-info.java`. `[API]` `[SOURCE]` `[VERSION-TRAP]`

3.10.14 `ServiceLoader`'s `LazyClassPathLookupIterator` instantiates each provider only when
        `next()` is called and **caches instantiated providers**, so a failing provider surfaces as a
        `ServiceConfigurationError` mid-iteration rather than at load time. `[TRAP]` `[SOURCE]`

3.10.15 `Charset.forName` / `CharsetProvider` and `Locale` / `LocaleServiceProvider` — the same
        provider pattern with an SPI; `-Djava.locale.providers=CLDR,COMPAT` and the JDK 9 switch of the
        default locale data from JRE to **CLDR** is the version delta that has broken date formats in
        real migrations. `[VERSION-TRAP]` `[API]`

3.10.16 `Calendar.getInstance()` — **static factory selecting an implementation** by locale
        (`GregorianCalendar`, `JapaneseImperialCalendar`, `BuddhistCalendar`). The reason it is worth
        naming is that it is a factory whose *return type is the abstract class*, so the caller cannot
        tell which it got — and `java.time` replaced the whole thing. `[API]` `[VERSION-TRAP]`

3.10.17 `Executors` — a **static factory** over one product: every method returns a configured
        `ThreadPoolExecutor` (or `ForkJoinPool`, or since JDK 21
        `newVirtualThreadPerTaskExecutor()`). `newFixedThreadPool` passes an **unbounded**
        `LinkedBlockingQueue`, which is the factory hiding the single most dangerous parameter in the
        JDK. `[TRAP]` `[X-REF 05]`

3.10.18 `Stream`'s pipeline is a **decorator/visitor hybrid**: `AbstractPipeline` links stages;
        each stateless intermediate op contributes a `Sink.ChainedReference` whose `accept` calls
        `downstream.accept` (decorator); `Spliterator.tryAdvance`/`forEachRemaining` is the traversal
        (iterator/visitor); the terminal op supplies the `TerminalOp` and `evaluate` runs it. `[SOURCE]`

3.10.19 `Spliterator`'s characteristic bits as the strategy inputs: `ORDERED`, `DISTINCT`, `SORTED`,
        `SIZED`, `NONNULL`, `IMMUTABLE`, `CONCURRENT`, `SUBSIZED` — the flags that let the pipeline
        skip work (e.g. `distinct()` on a `DISTINCT` source). `[API]` `[NUM]`

3.10.20 `EnumSet.noneOf(Class<E>)` — a **factory choosing a representation**: it reads the enum's
        universe and returns `RegularEnumSet` (one `long` bit vector) if `universe.length <= 64`,
        otherwise `JumboEnumSet` (`long[]`). Also `ThreadLocalRandom.current()` as
        thread-specific-storage-as-factory, and `Collections.emptyList()`/`Comparator.naturalOrder()`
        as **null-object/singleton** factories. `[SOURCE]` `[NUM]` `[API]`

*(20 leaves)*

## §3.11 Filter chains: `ApplicationFilterChain` and the Spring Security chain

3.11.1 `org.apache.catalina.core.ApplicationFilterChain` fields, read off the source:
       `private ApplicationFilterConfig[] filters = new ApplicationFilterConfig[0]`,
       `private int pos = 0` (current position), `private int n = 0` (number of filters),
       `private Servlet servlet = null`, `private boolean servletSupportsAsync = false`,
       `private boolean dispatcherWrapsSameObject = false`, and
       `public static final int INCREMENT = 10`. The chain is an **array plus a counter**, not a linked
       list. `[SOURCE]` `[API]`

3.11.2 `public void doFilter(ServletRequest request, ServletResponse response)` is the whole public
       entry point in current Tomcat: `if (pos < n) { var filterConfig = filters[pos++]; var filter =
       filterConfig.getFilter(); filter.doFilter(request, response, this); return; }` — then, after the
       array is exhausted, `servlet.service(request, response)`. `[SOURCE]` `[FLOW]` `[API]`

3.11.3 `[VERSION-TRAP]` **`internalDoFilter` — the frame you will see in stack traces and will not find
       in the source.** Verified per release: `private void internalDoFilter(ServletRequest,
       ServletResponse)` **exists in Tomcat 9.0.x and 10.1.x** and **does not exist in Tomcat 11.0.x or
       `main`**, where `doFilter` holds the loop directly. The cause is traceable: in 9.0.x/10.1.x
       `doFilter` was a thin wrapper that branched on `Globals.IS_SECURITY_ENABLED` and, when set, ran
       `AccessController.doPrivileged((PrivilegedExceptionAction<Void>) () -> { internalDoFilter(req,
       res); return null; })`. Tomcat 11 dropped SecurityManager support, the `doPrivileged` wrapper
       went with it, and the private method had no remaining reason to exist. So a
       `ApplicationFilterChain.internalDoFilter` frame in a stack trace dates the server at ≤ 10.1.x —
       and every blog citing it is describing a version the reader may not be running.
       `[SOURCE]` `[DIAG]`

3.11.4 The mechanism worth stating out loud: **`this` is passed as the `FilterChain`**, so the chain is
       re-entered by the filter calling `chain.doFilter(...)`, and `pos++` has already advanced. The
       recursion is on the stack, which is why a 20-filter chain is 20 nested frames in every stack
       trace. `[PROVE]` `[DIAG]`

3.11.5 `INCREMENT = 10` is the array growth step in `addFilter`: when `n == filters.length`, a new array
       of `n + INCREMENT` is allocated and copied. Linear growth, not doubling — trivia, but it is the
       evidence the structure is a plain array sized for a handful of filters. `[SOURCE]` `[NUM]`

3.11.6 The `static final ThreadLocal<ServletRequest> lastServicedRequest` /
       `lastServicedResponse` pair (exposed by `getLastServicedRequest`/`getLastServicedResponse`) is
       populated only when `ApplicationDispatcher.WRAP_SAME_OBJECT` is enabled — a debugging affordance,
       and a `ThreadLocal` on a pooled request thread, which is the leak shape from §1.12.
       `[SOURCE]` `[TRAP]`

3.11.7 Not calling `chain.doFilter` is the **short-circuit**, and it is the entire mechanism by which an
       auth filter returns 401 without the controller ever existing. Code before the call is request
       processing; code after it is response processing. `[PROVE]`

3.11.8 `[TRAP]` Writing to the response *after* `chain.doFilter` returns fails with
       `IllegalStateException: Cannot call sendError() after the response has been committed` — the
       downstream already committed. Response-side filter logic must run before commit or wrap the
       response.

3.11.9 Spring Security is **one servlet filter**: `DelegatingFilterProxy` (registered with the
       container) → `FilterChainProxy` (the Spring bean) → a `List<SecurityFilterChain>`, each a
       `RequestMatcher` plus its own filter list. `[SOURCE]` `[API]` `[X-REF 13]`

3.11.10 `FilterChainProxy.doFilterInternal` selects the **first** matching `SecurityFilterChain` via
        `getFilters(request)` and builds a `VirtualFilterChain` over it. First match wins — a broader
        matcher declared earlier silently shadows a narrower one declared later. `[SOURCE]` `[TRAP]`

3.11.11 `FilterChainProxy.VirtualFilterChain` is the private inner chain driver: fields
        `List<Filter> additionalFilters`, `int currentPosition`, `FilterChain originalChain`. When
        `currentPosition == size`, it delegates to `originalChain.doFilter` — handing control back to
        Tomcat's `ApplicationFilterChain`. Two nested chain-of-responsibility implementations of the
        same shape, one array-and-counter, one list-and-counter. `[SOURCE]` `[PROVE]`

3.11.12 `OncePerRequestFilter.doFilter` skips when the request already carries the attribute named by
        `getAlreadyFilteredAttributeName()` — by default `getFilterName() + ALREADY_FILTERED_SUFFIX`,
        where the suffix constant's value is `".FILTERED"`. Plus `shouldNotFilter(request)`,
        `shouldNotFilterAsyncDispatch()` (returns `true` by default) and
        `shouldNotFilterErrorDispatch()` (returns `true` by default). `[SOURCE]` `[API]` `[RESEARCH]`

3.11.13 The ordering mechanisms, all three and which wins where: `@Order`/`Ordered` on a `Filter` bean,
        `FilterRegistrationBean.setOrder(int)` in Boot, and `HttpSecurity`'s fixed
        `FilterOrderRegistration` inside a `SecurityFilterChain` (where you insert relative to a known
        filter with `addFilterBefore`/`addFilterAfter`, not by number). `[TABLE]` `[API]`

3.11.14 Why order is a **security property**, stated as the `ApplicationGateway` case: it terminates
        client TLS and **strips the client token** (§6.2), so a logging filter ordered before the
        stripping filter writes client tokens to disk. Order is not configuration; it is the control.
        `[INCIDENT]` `[X-REF 13]`

*(14 leaves)*

## §3.12 Records: what the compiler generates, and the immutability it does and does not give

3.12.1 A `record` is a `final` class extending `java.lang.Record` (abstract, in `java.lang`), and it
       cannot extend anything else. `Record` declares `equals`, `hashCode` and `toString` as
       **abstract**, which is how the compiler is forced to provide them. `[SOURCE]` `[API]`

3.12.2 `javac` generates one `private final` field per component and one **accessor named exactly like
       the component** — `stakeId()`, not `getStakeId()`. The accessor is `public final`. `[SOURCE]`

3.12.3 The **canonical constructor** takes all components positionally in declaration order. It is
       `public` if the record is `public`; you may not weaken its access. `[API]` `[TRAP]`

3.12.4 The **compact constructor** (`public StakeReservation { ... }`, no parameter list) is the
       validation and normalisation hook: the parameters are mutable locals, and `javac` appends
       `this.x = x;` for every component **after** your body. So assigning `weights = Map.copyOf(weights)`
       in the body is what actually stores the copy. `[SOURCE]` `[PROVE]`

3.12.5 `[TRAP]` Writing `this.weights = Map.copyOf(weights)` inside a *compact* constructor is a compile
       error ("cannot assign a value to final variable" / instance field assignment not allowed) — you
       assign the **parameter**, not the field. This is the single most common record mistake.

3.12.6 `equals`, `hashCode` and `toString` are **not** emitted as bytecode bodies: each is a one-line
       `invokedynamic` against `java.lang.runtime.ObjectMethods.bootstrap`. `[SOURCE]` `[API]`

3.12.7 `ObjectMethods.bootstrap(MethodHandles.Lookup lookup, String methodName, TypeDescriptor type,
       Class<?> recordClass, String names, MethodHandle... getters)` — "a bootstrap method to generate
       the `Object.equals`, `Object.hashCode` and `Object.toString` methods, based on a description of
       the component names and accessor methods, for either invokedynamic call sites or dynamic
       constant pool entries". `methodName` must be one of `"equals"`, `"hashCode"`, `"toString"`.
       `[SOURCE]` `[API]`

3.12.8 The consequence of the indy indirection: the *first* call links the method handle chain
       (a one-time cost), and thereafter it is JIT-inlined like handwritten code — so "records are
       slower because of invokedynamic" is a startup-cost claim, not a steady-state one.
       `[TRAP]` `[X-REF 25]`

3.12.9 `equals` semantics: component-wise, using `==` for primitives (with `Float.compare`/
       `Double.compare` for floating point, so `NaN` equals `NaN` and `+0.0 != -0.0`) and
       `Objects.equals` for references. `hashCode` is derived from the components but its exact
       algorithm is **unspecified** and may change between releases — never persist a record's hash.
       `[TRAP]` `[SOURCE]`

3.12.10 You may **override** an accessor or `equals`/`hashCode`/`toString`; `@Override` on an accessor
        is legal and is the recommended marker. Overriding an accessor to return a defensive copy is
        the sanctioned way to close the array-component hole. `[API]` `[DECIDE]`

3.12.11 What you may **not** do: declare an instance field, declare a non-`static` initialiser block,
        make the record non-`final`, extend a class, or declare a native method. `[TABLE]`

3.12.12 The reflection surface: `Class.isRecord()`, `Class.getRecordComponents()` returning
        `RecordComponent[]`, and `RecordComponent.getName()`/`getType()`/`getAccessor()`/
        `getGenericType()`/`getAnnotations()`. This is what Jackson's and Hibernate's record support is
        built on. `[API]`

3.12.13 **Shallow immutability, with the exact gap**: the component *references* are `final`; the
        referents are not. `record Reservation(String id, List<Leg> legs)` — `r.legs().add(...)`
        mutates a "immutable" record. Closed by `List.copyOf(legs)` in the compact constructor.
        `[TRAP]` `[PROVE]`

3.12.14 The **array component** is the gap `copyOf` does not close by itself: an array component is
        copied by `clone()` in the constructor *and* must be copied again in the accessor, because
        otherwise the caller holds the internal array. Also: `equals` on an array component uses
        `Objects.equals`, i.e. **reference identity**, so two records with equal array contents are not
        equal. `[TRAP]` `[PROVE]`

*(14 leaves)*

## §3.13 Sealed types and exhaustive switch: `PermittedSubclasses`, `typeSwitch` bootstrap, `MatchException` — the mechanism that retires visitor

3.13.1 `sealed interface RestrictionOutcome permits Allowed, Blocked, Limited` — `sealed` plus an
       explicit `permits` clause. The `permits` clause may be **omitted** when all permitted subtypes
       are in the same source file, in which case `javac` infers it. `[API]` `[SOURCE]`

3.13.2 Every permitted subclass must be `final`, `sealed`, or explicitly `non-sealed`. There is no
       fourth option — `non-sealed` exists precisely so a hierarchy can be deliberately reopened at one
       point. `[API]` `[TRAP]`

3.13.3 The same-module/same-package rule: a sealed type and its permitted subclasses must be in the
       same **module**, or, if in an unnamed module, the same **package**. This is the JPMS-level
       enforcement (see §3.20). `[SOURCE]` `[X-REF 04]`

3.13.4 The class-file mechanism: `javac` writes a **`PermittedSubclasses`** attribute on the sealed
       class — a list of constant-pool class references. `Class.isSealed()` and
       `Class.getPermittedSubclasses()` read it. The *class file*, not an annotation, carries the
       constraint. `[SOURCE]` `[API]`

3.13.5 The **JVM** enforces it at class load: defining a class that names a sealed class as its
       supertype without appearing in that class's `PermittedSubclasses` fails verification with an
       `IncompatibleClassChangeError`. Sealing is not a compiler convention. `[SOURCE]` `[PROVE]`

3.13.6 Exhaustive `switch` over a sealed hierarchy: `javac` proves exhaustiveness from
       `PermittedSubclasses` and **allows the omission of `default`**. Adding a permitted subtype then
       breaks compilation at every such switch — the "every visitor must handle every type" guarantee,
       enforced by the compiler instead of by an `accept`/`visit` pair. `[PROVE]`

3.13.7 A pattern `switch` on a reference type compiles to `invokedynamic` against
       `java.lang.runtime.SwitchBootstraps.typeSwitch(MethodHandles.Lookup, String, MethodType,
       Object... labels)` — "a bootstrap method for linking an invokedynamic call site that implements
       a switch on a target of a reference type". `[SOURCE]` `[API]`

3.13.8 The `labels` static arguments must be non-null and of type `String`, `Integer`, `Class`, or
       `EnumDesc`. The call site returns the **index** of the first matching label (or the number of
       labels if none matched, or `-1` for a `null` target), and `javac` emits a `tableswitch` on that
       int. So a pattern switch is: one indy call returning an index, then a dense integer switch.
       `[SOURCE]` `[PROVE]` `[NUM]`

3.13.9 `SwitchBootstraps.enumSwitch` is the sibling bootstrap for enum patterns. Both are in
       `java.lang.runtime`, both were preview in 17–20 and final in **21** (JEP 441). `[API]`
       `[VERSION-TRAP]`

3.13.10 The linear-scan cost: the generated matcher tests labels **in order**, so a hot pattern switch
        over 11 restriction types averages ~5.5 `instanceof`-equivalent tests. On `ClientRestrictions`'
        30 ms budget this is noise; in a per-ledger-entry loop it is worth ordering the common case
        first. `[NUM]` `[DECIDE]`

3.13.11 **`MatchException`** (`java.lang.MatchException`, `extends RuntimeException`, `final`) is what
        an exhaustive switch throws at run time when no label applies. Introduced in the pattern-switch
        preview and final in JDK 21. `[API]` `[SOURCE]`

3.13.12 **The release boundary, stated explicitly because this project has had it backwards:**
        `MatchException` is the JDK 21 baseline answer. **JEP 433 (JDK 20, fourth preview)** carried the
        release note: *"An exhaustive switch (i.e., a switch expression or a pattern switch statement)
        over an enum class **now throws `MatchException` rather than `IncompatibleClassChangeError`** if
        no switch label applies at run time."* Before JDK 20, an exhaustive **enum** switch threw
        `IncompatibleClassChangeError`. From JDK 20 preview / **JDK 21 final** onward it throws
        `MatchException`, for enum, sealed and pattern switches alike. `[SOURCE]` `[VERSION-TRAP]` `[NUM]`

3.13.13 `IncompatibleClassChangeError` has **not** disappeared — it remains the error for genuine
        incompatible class changes, including the sealing violation in §3.13.5 and older
        separately-compiled-switch scenarios. The two are not synonyms and the boundary is
        "no label applied" (`MatchException`) versus "the class shape is illegal" (`ICCE`).
        `[TRAP]` `[PROVE]`

3.13.14 The scenario that produces `MatchException` in production: a library ships
        `sealed interface RestrictionOutcome permits Allowed, Blocked`; a consumer compiles an
        exhaustive switch; the library adds `Limited` and is upgraded **without recompiling the
        consumer**. The consumer's switch was exhaustive at compile time and is not at run time.
        `[INCIDENT]` `[FLOW]`

3.13.15 The mitigation from OpenJDK's own exhaustiveness guide: for a sealed API you expect to evolve,
        either keep a `default` (giving up the compile-time check for forward compatibility) or treat
        adding a permitted subtype as a **binary-incompatible change** and version accordingly. There
        is no option that is both exhaustive and forward-compatible. `[SOURCE]` `[DECIDE]`

3.13.16 The conclusion for visitor: for a **closed** hierarchy, sealed + exhaustive switch delivers
        visitor's guarantee with no `accept`, no `visit`, no double dispatch, and the errors at compile
        time; for an **open** hierarchy it delivers nothing and visitor (or a plain interface method)
        remains the answer. The discriminator is `permits`, not taste. `[DECIDE]` `[SAY]`

*(16 leaves)*

## §3.14 Immutability at JIT level: trusted finals, constant folding, and the safe-publication guarantee

3.14.1 `static final` fields of constant-expression primitive/`String` type are folded by **`javac`**
       into the reading class's constant pool — before the JVM is involved (§3.3.2). `[SOURCE]`

3.14.2 `static final` fields of *reference* type are folded by **C2**: once the holder class is
       initialised, the field's value is a known constant, so C2 treats it as such and can then
       devirtualise calls on it and fold its own `final` fields transitively. `[PROVE]`

3.14.3 Non-static `final` fields are **not** trusted by default. HotSpot's default trust set is:
       `java/lang/invoke` and `sun/invoke` packages, VM/hidden classes, **record classes**, all boxed
       classes, `java.lang.String`, and the `Atomic*FieldUpdater` implementations. `[SOURCE]` `[NUM]`

3.14.4 `-XX:+TrustFinalNonStaticFields` — an **experimental** flag (requires
       `-XX:+UnlockExperimentalVMOptions`), **off by default**, that extends that trust to all `final`
       instance fields. `[API]` `[NUM]`

3.14.5 Shipilev's measurement of the effect: without the flag, `_static_final` = **4.202 ± 0.002 ns/op**
       and `_inst_final` = **4.317 ± 0.002 ns/op**; with the flag, `_static_final` drops to
       **1.901 ± 0.001 ns/op**. `[NUM]` `[SOURCE]` `[PROVE]`

3.14.6 Why it is not on by default, in the JDK's own terms: frameworks mutate `final` fields through
       reflection, `Unsafe` and JNI in violation of the JLS, and "the potential breakage from
       misbehaving applications may severely dampen" the gain. The flag is a bet on your dependencies'
       hygiene. `[SOURCE]` `[DECIDE]`

3.14.7 That **record classes are in the default trust set** is the load-bearing fact for this topic: it
       is a JIT-level reward for using records as value objects, not just an ergonomic one.
       `[PROVE]` `[SAY]`

3.14.8 The second JIT consequence of immutability: no write barrier. A field that is never written after
       construction never pays the G1 card-marking / SATB barrier that a mutable field pays on every
       store — which at `FundsLedger`'s 19.8M entries/day is a real allocation-path cost.
       `[NUM]` `[X-REF 06]`

3.14.9 The third: an immutable object needs no defensive copy at any boundary, so the copies that
       *would* have been allocated are not allocated, and the ones that remain are usually NoEscape
       (§3.2). Immutability's biggest performance effect is the allocations it deletes, not the field
       reads it speeds up. `[PROVE]`

3.14.10 The safe-publication guarantee restated as the JIT's precondition: C2 may fold a `final` field
        only because §17.5's freeze forbids observing it pre-initialisation — so a `this`-escape
        (§3.4.10) is not merely a JMM bug, it invalidates a compiler assumption. `[PROVE]` `[X-REF 06]`

*(10 leaves)*

## §3.15 Resilience4j internals: the state machine, the sliding windows, the CAS on state transition

3.15.1 `io.github.resilience4j.circuitbreaker.internal.CircuitBreakerStateMachine implements
       CircuitBreaker` is the whole implementation. Fields:
       `private final String name`, `private final AtomicReference<CircuitBreakerState>
       stateReference`, `private final CircuitBreakerConfig circuitBreakerConfig`,
       `private final Map<String, String> tags`, `private final CircuitBreakerEventProcessor
       eventProcessor`, `private final Clock clock`, `private final SchedulerFactory schedulerFactory`,
       `private final Function<Clock, Long> currentTimestampFunction`,
       `private final TimeUnit timestampUnit`, `private final ReentrantLock lock`. `[SOURCE]` `[API]`

3.15.2 The state is an **object, not an enum**: `CircuitBreakerState` is an abstract class with the
       inner implementations `ClosedState`, `OpenState`, `HalfOpenState`, `DisabledState`,
       `ForcedOpenState`, `MetricsOnlyState`. Each holds its own `CircuitBreakerMetrics`. That is the
       **State pattern**, and the state object decides its own successor — §1.22's discriminator made
       concrete. `[SOURCE]` `[PROVE]`

3.15.3 The public `CircuitBreaker.State` enum, quoted from `CircuitBreaker.java` — **six** constants,
       not three, each carrying `(order, allowPublish)`: `DISABLED(3, false)`, `METRICS_ONLY(5, true)`,
       `CLOSED(0, true)`, `OPEN(1, true)`, `FORCED_OPEN(4, false)`, `HALF_OPEN(2, true)`. The
       `allowPublish` flag is the mechanism by which `DISABLED` and `FORCED_OPEN` emit no events, and
       `METRICS_ONLY` is the "measure before you enforce" rollout mode most teams do not know exists:
       its javadoc says it is "collecting metrics, publishing events and allowing all requests through
       but is not transitioning to other states". `[SOURCE]` `[API]` `[NUM]`

3.15.4 The companion `CircuitBreaker.StateTransition` enum enumerates the legal transitions explicitly
        (`CLOSED_TO_OPEN`, `HALF_OPEN_TO_CLOSED`, …) — **33** named constants over the 6 states, which
        is the state machine's transition table expressed as a type rather than as `if`s. This is
        §1.22's "make illegal states unrepresentable" applied to the *transitions*, not the states.
        `[SOURCE]` `[NUM]`

3.15.5 Transitions go through `stateReference.compareAndSet(current, next)` /
       `getAndUpdate(...)`, so a losing thread's transition is simply dropped rather than applied
       twice. The transition methods, named: `transitionToClosedState()`, `transitionToOpenState()`,
       `transitionToOpenStateFor(Duration)`, `transitionToOpenStateUntil(Instant)`,
       `transitionToHalfOpenState()`, `transitionToDisabledState()`,
       `transitionToMetricsOnlyState()`, `transitionToForcedOpenState()`. `[SOURCE]` `[API]`

3.15.6 The `ReentrantLock` alongside the `AtomicReference` is the detail that catches people out: CAS
       guards the state *value*, the lock serialises the *event publication and callback* so listeners
       see transitions once and in order. Lock-free state, locked notification. `[SOURCE]` `[PROVE]`

3.15.7 `ClosedState`'s constructor calls `CircuitBreakerMetrics.forClosed(getCircuitBreakerConfig())`;
       `HalfOpenState` uses `forHalfOpen(permittedNumberOfCallsInHalfOpenState, config)`. The metrics
       object is **per state instance**, which is why a transition resets the window. `[SOURCE]` `[PROVE]`

3.15.8 The window implementations, by name: count-based → `FixedSizeSlidingWindowMetrics` (and
       `LockFixedSizeSlidingWindowMetrics`); time-based → `SlidingTimeWindowMetrics` (and
       `LockFreeSlidingTimeWindowMetrics`). `CircuitBreakerMetrics` holds
       `private final Metrics metrics` and `private int minimumNumberOfCalls`. `[SOURCE]` `[API]`

3.15.9 `[VERSION-TRAP]` The **ring-bit-buffer / `RingBitSet`** representation — a `BitSet` of 16 `long`s
       storing 1024 call outcomes as 0 = success, 1 = failure — is **Resilience4j 0.x/1.0-era**.
       Verified: `RingBitSet` appears **nowhere** in current `CircuitBreaker.java` or
       `CircuitBreakerMetrics.java` on `master`. From 1.x onward the count-based window is
       `FixedSizeSlidingWindowMetrics`: a circular `Measurement[]` of `slidingWindowSize` entries
       holding duration and outcome, with a running `TotalAggregation`. Every blog describing the ring
       bit buffer — and Resilience4j's own older readme.io pages — is describing a version you are not
       running. `[SOURCE]`

3.15.10 `FixedSizeSlidingWindowMetrics.record(...)` is O(1): it moves the head, **subtracts** the evicted
       measurement from the total aggregation and **adds** the new one. It does not rescan the window —
       which is why `slidingWindowSize` costs memory, not CPU. `[PROVE]` `[NUM]`

3.15.11 `SlidingTimeWindowMetrics` is a circular array of **per-second partial aggregations** of size
        `slidingWindowSize` (in seconds), each rotated and zeroed as the clock advances. So a
        60-second window is 60 buckets, and the resolution is 1 second — not continuous. `[NUM]` `[SOURCE]`

3.15.12 **The authoritative config surface for this whole syllabus** — every default quoted from the
        `DEFAULT_*` constants in
        `resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreakerConfig.java`
        on `master`. Any other section quoting a default defers to this leaf. `[SOURCE]` `[NUM]` `[API]` `[TABLE]`

        | Builder property | Constant | Value |
        |---|---|---|
        | `failureRateThreshold` | `DEFAULT_FAILURE_RATE_THRESHOLD` | `50` (percent) |
        | `slowCallRateThreshold` | `DEFAULT_SLOW_CALL_RATE_THRESHOLD` | `100` (percent) |
        | `slowCallDurationThreshold` | `DEFAULT_SLOW_CALL_DURATION_THRESHOLD` | `60` (seconds) |
        | `waitDurationInOpenState` | `DEFAULT_WAIT_DURATION_IN_OPEN_STATE` | `60` (seconds) |
        | `permittedNumberOfCallsInHalfOpenState` | `DEFAULT_PERMITTED_CALLS_IN_HALF_OPEN_STATE` | `10` |
        | `maxWaitDurationInHalfOpenState` | `DEFAULT_WAIT_DURATION_IN_HALF_OPEN_STATE` | `0` (wait indefinitely) |
        | `minimumNumberOfCalls` | `DEFAULT_MINIMUM_NUMBER_OF_CALLS` | `100` |
        | `slidingWindowSize` | `DEFAULT_SLIDING_WINDOW_SIZE` | `100` |
        | `slidingWindowType` | `DEFAULT_SLIDING_WINDOW_TYPE` | `SlidingWindowType.COUNT_BASED` |
        | `transitionToStateAfterWaitDuration` | `DEFAULT_TRANSITION_TO_STATE_AFTER_WAIT_DURATION` | `State.OPEN` |
        | `writableStackTraceEnabled` | `DEFAULT_WRITABLE_STACK_TRACE_ENABLED` | `true` |

        `public enum SlidingWindowType { TIME_BASED, COUNT_BASED }` — two constants, and the enum is
        nested in `CircuitBreakerConfig`.

3.15.13 Two properties that are **not** in the `DEFAULT_*` block, so their defaults are field
         initialisers I did not read: `automaticTransitionFromOpenToHalfOpenEnabled` (believed `false`)
         and `maxWaitDurationInHalfOpenState`'s interaction with
         `DEFAULT_WAIT_DURATION_IN_HALF_OPEN_STATE = 0`. The `= 0` is confirmed and means "no time
         limit — wait for `permittedNumberOfCallsInHalfOpenState` calls however long that takes",
         which is the mechanism behind §3.15.17. The `automaticTransition...` default is
         **unconfirmed**; see the notes block. `[RESEARCH]` `[API]`

3.15.14 `[NUM]` The arithmetic that makes the defaults dangerous, stated once: `minimumNumberOfCalls =
         100` **and** `slidingWindowSize = 100` means the breaker needs 100 calls *in the window* before
         it computes a rate at all, and the window is **per breaker instance, per JVM**. Across
         `DocumentVerification`'s 6 instances that is 600 estate-wide calls before any instance can
         open. Every incident in §3.22.6 follows from these two numbers being equal and large.

3.15.15 `minimumNumberOfCalls` is the gate, and the source shows the mechanism exactly:
        `if (bufferedCalls == 0 || bufferedCalls < minimumNumberOfCalls) return -1.0f;` — the
        **`-1.0f` sentinel** — and `checkIfThresholdsExceeded()` maps `-1` to
        `Result.BELOW_MINIMUM_CALLS_THRESHOLD`, which prevents any transition. `[SOURCE]` `[NUM]` `[PROVE]`

3.15.16 `[TRAP]` The default pairing `minimumNumberOfCalls = 100` with `slidingWindowSize = 100` is the
        breaker-that-never-opens configuration for a low-traffic path: the identity-vendor call in
        `DocumentVerification` at 24k uploads/day spread over 6 instances may not reach 100 calls in a
        window before the outage ends. Symptom: the dependency is dead, the breaker is `CLOSED`, and
        every call burns its full 38 s p99. `[INCIDENT]` `[NUM]`

3.15.17 `[TRAP]` The breaker-that-never-closes mirror: with
        `automaticTransitionFromOpenToHalfOpenEnabled` **off** (believed the default — see §3.15.13),
        the transition to `HALF_OPEN` happens **on the next call attempt**, not on a timer, because
        `OpenState` only checks its wait-duration clock when a call asks permission. If upstream has
        also given up calling (or a bulkhead is rejecting first), the breaker sits `OPEN` indefinitely
        and recovery never gets probed. `[INCIDENT]` `[NUM]`

3.15.18 `HalfOpenState` admits exactly `permittedNumberOfCallsInHalfOpenState` calls and rejects the
        rest with `CallNotPermittedException`; when that many results are in, it evaluates the failure
        rate and transitions to `CLOSED` or back to `OPEN`. Note that **rejections are not failures** —
        `CallNotPermittedException` is not recorded in the window, or the breaker would feed itself.
        `[PROVE]` `[API]`

3.15.19 **Decorator composition order.** `Decorators.ofSupplier(...)` applies in the order
        `Bulkhead → TimeLimiter → RateLimiter → CircuitBreaker → Retry`, i.e. **`Retry` is the
        outermost**, so each retry attempt is a separate call *through* the breaker and is counted by
        it. That is the order you want: the breaker sees the amplified load and can open. Put `Retry`
        **inside** the breaker and the breaker counts one logical call per N attempts, so it opens
        N times too late while the dependency takes N times the load — the retry-amplification
        mechanism in §3.22.1. `[DECIDE]` `[PROVE]` `[NUM]`

*(19 leaves)*

## §3.16 Event-sourcing internals: the append-only log, version-based optimistic concurrency, snapshotting, upcasting

3.16.1 The event-store table shape, column by column: `aggregate_id UUID`, `version BIGINT`,
       `event_type VARCHAR`, `payload JSONB/BYTEA`, `metadata JSONB` (correlation id, causation id,
       actor, role — §6.3), `occurred_at TIMESTAMPTZ`, `global_sequence BIGSERIAL`. `[API]` `[BUILD]`

3.16.2 `UNIQUE (aggregate_id, version)` **is** the optimistic concurrency control. There is no separate
       lock, no `SELECT ... FOR UPDATE`, no version column to compare: two concurrent commands both
       read version 47, both try to insert version 48, and the database rejects one with a unique-key
       violation. `[PROVE]` `[SOURCE]`

3.16.3 The Java-side translation: Postgres SQLSTATE **23505** (`unique_violation`) →
       `DataIntegrityViolationException` → caught and rethrown as a domain
       `ConcurrentModificationException`/`OptimisticLockException`, then retried by reloading and
       re-deciding. Catching the *right* exception is the whole implementation. `[API]` `[DIAG]`

3.16.4 The append is **insert-only** — no `UPDATE`, no `DELETE`. Enforced, not hoped for: a
       `BEFORE UPDATE OR DELETE` trigger that raises, or a role with `INSERT, SELECT` grants only.
       An append-only log that the application *could* update is not a log. `[BUILD]` `[DECIDE]`

3.16.5 `global_sequence` gives a total order for projections to follow, but it is **not gap-free**: a
       `BIGSERIAL` advances on rolled-back transactions, so a projection that assumes contiguity stalls
       forever on a gap. Consume by "greater than my last seen", never "equals last + 1".
       `[TRAP]` `[PROVE]`

3.16.6 The replay loop, as a flow: `SELECT payload, event_type, version FROM events WHERE aggregate_id
       = ? AND version > ? ORDER BY version` → deserialise → `for (e : events) state = apply(state, e)`
       → set `state.version` to the last event's version. `apply` must be **pure and total** — no I/O,
       no clock, no random, and no throwing on an old event. `[FLOW]` `[PROVE]`

3.16.7 `[TRAP]` Validation inside `apply`. The command handler validates; `apply` only folds. An
       `apply` that rejects a historically-valid event makes the aggregate permanently unloadable —
       the event happened, and the past is not negotiable.

3.16.8 Snapshotting: a `snapshots(aggregate_id, version, state, created_at)` row; load = latest
       snapshot + events with `version > snapshot.version`. The snapshot is a **memento** (§1.28) and
       must be treated as a cache — deletable and rebuildable, never the source of truth. `[PROVE]`

3.16.9 The snapshot-cadence arithmetic for `FundsLedger`: **19.8M entries/day** across
       **2.4M registered clients** is ~8 events/client/day, so a client's position aggregate reaches
       ~2,900 events/year. At a 4-entry stake reservation and a monthly-active base of 380k, the
       *active* client accrues ~52 events/day → ~19k/year. A snapshot every **200 events** bounds
       replay at 200 rows × 180 bytes = **36 KB** and one index seek. `[NUM]` `[PROVE]`

3.16.10 The cadence trade stated as the decision procedure: snapshot every N events where N × row-read
        cost ≤ your load-latency budget. Against the **80 ms balance-read budget**, 200 events is two
        orders of magnitude of headroom; against the **150 ms stake-reservation budget** with a write
        in the same transaction, it is still comfortable. Snapshot on a *schedule* instead and the
        worst case is unbounded. `[DECIDE]` `[NUM]`

3.16.11 `[TRAP]` The snapshot that embeds the serialised domain object (Java serialization, or Jackson
        with default typing) welds the store to a class shape. Snapshots must serialise a **versioned
        DTO**, or the next refactor makes every snapshot unreadable — and unlike events, that is
        survivable only because you can delete them all and replay.

3.16.12 Event versioning strategies, all four, with the cost of each: (1) **weak schema** — additive-only
        fields with defaults; (2) **upcasting** — an `EventUpcaster` chain transforming v1 payload → v2
        at read time; (3) **multiple versions in the type name** (`StakeReserved.v2`) with a handler per
        version; (4) **copy-and-replace** — a one-off migration writing a new stream. `[TABLE]` `[DECIDE]`

3.16.13 The upcaster mechanism concretely: registered as an ordered chain keyed by
        (event type, version), each step raising the payload one version, so a v1 event read in 2029
        passes through three upcasters before reaching `apply`. The chain must be **kept forever**, and
        it is code with no tests unless you keep a corpus of old payloads. `[PROVE]` `[BUILD]`

3.16.14 `[INCIDENT]` The schema-evolution failure mode: a developer **renames** a field on
        `StakeReserved` (or changes `amount` from minor units to a decimal string) and deploys. Symptom:
        replay of aggregates last touched before the deploy throws `MismatchedInputException` /
        yields `null` amounts; positions load as zero; balance reads return wrong money. Diagnosis path:
        the failure is version-correlated (only old streams break), the error is in deserialisation not
        in business logic, and `occurred_at` on failing events all precede the deploy. Root cause: a
        field rename is a **wire-format** change on an immutable log. Fix: revert, add an upcaster,
        redeploy — and add a test that deserialises a frozen corpus of every historical payload shape.

3.16.15 GDPR erasure against an append-only log, mechanism named: **crypto-shredding** — encrypt each
        subject's PII payload fields with a per-subject key held in a separate keystore, and delete the
        key. The events remain, the plaintext does not. The cost is that replay of a shredded stream
        yields events with unreadable fields, so `apply` must tolerate them. `[DECIDE]` `[X-REF 13]`

3.16.16 Why CQRS is **not optional** here (the constraint, not a preference): the log answers exactly
        one query — "events for aggregate X in version order". "All withdrawals for client Y" (§7.3) is
        unanswerable against it, so a projection is mandatory and its lag is a permanent property of
        the design. `[PROVE]` `[X-REF 22]`

*(16 leaves)*

## §3.17 Outbox internals: same-transaction insert, polling vs CDC, ordering, dedup, relay idempotence

3.17.1 The problem the outbox exists to solve, stated as the impossibility: a database write and a
       broker publish cannot be made atomic without a distributed transaction, so any code that does
       both has a window where one succeeded and the other did not. The outbox removes the second
       resource from the transaction rather than coordinating it. `[PROVE]`

3.17.2 The table: `outbox(id UUID PK, aggregate_type, aggregate_id, event_type, payload JSONB,
       created_at TIMESTAMPTZ, processed_at TIMESTAMPTZ NULL, attempts INT DEFAULT 0)`. Plus the index
       that makes the relay query sargable: `CREATE INDEX ON outbox (created_at) WHERE processed_at IS
       NULL` — a **partial index**, so it stays small as the table grows. `[API]` `[BUILD]` `[NUM]`

3.17.3 The same-transaction insert is the entire correctness argument: the ledger entries and the
       outbox row are inserted **in one local ACID transaction**, so the event exists if and only if
       the state change committed. `[PROVE]`

3.17.4 `[TRAP]` The version that looks identical and is broken: publishing in an
       `@TransactionalEventListener(phase = AFTER_COMMIT)` (§3.19). The commit succeeded, the publish
       is outside it, and a crash between them loses the event silently. After-commit publication is
       *better* than in-transaction publication and is still **not** an outbox.

3.17.5 The relay's polling query: `SELECT * FROM outbox WHERE processed_at IS NULL ORDER BY created_at
       FOR UPDATE SKIP LOCKED LIMIT 100`. `FOR UPDATE` takes row locks; **`SKIP LOCKED`** is what lets
       N relay instances poll the same table concurrently without blocking each other or double-sending.
       `[SOURCE]` `[API]` `[PROVE]`

3.17.6 `SKIP LOCKED` semantics that matter: it skips rows locked by *any* transaction, so a relay
       instance that hangs mid-batch holds its rows until its transaction ends — the rows are not lost
       but they are delayed by the hung instance's transaction lifetime, not by the poll interval.
       `[TRAP]` `[PROVE]`

3.17.7 `NOWAIT` and plain `FOR UPDATE` as the wrong choices here: `NOWAIT` errors instead of skipping;
       plain `FOR UPDATE` serialises the relays. Naming why the alternatives fail is the source-level
       answer. `[DECIDE]`

3.17.8 **CDC / Debezium** as the other relay: it reads the Postgres **WAL** through a logical
       replication slot rather than polling, so there is no query load, no poll interval, and no
       `processed_at` update. Costs: a replication slot that **retains WAL** if the connector stalls
       (a disk-full outage mechanism), Kafka Connect to operate, and payload shape dictated by the
       table rather than by you. `[DECIDE]` `[API]` `[X-REF 14]`

3.17.9 The Debezium **outbox event router** (`io.debezium.transforms.outbox.EventRouter`) as the
       middle path: still an outbox table, but CDC-read, with `aggregate_id` routed to the Kafka message
       key and `payload` unwrapped into the value. `[API]` `[RESEARCH]`

3.17.10 The delivery guarantee is **at-least-once**, and the mechanism is unavoidable: the relay
        publishes, then marks `processed_at`. A crash between the two republishes. Making it
        exactly-once would need the same atomicity the outbox exists because you cannot have.
        `[PROVE]` `[TRAP]`

3.17.11 Therefore **consumer idempotence is mandatory, not defensive**: a `processed_events(event_id
        PK)` table inserted in the consumer's own transaction, with the primary-key violation as the
        duplicate detector. The **unique index is the mechanism** — check-then-insert is a race.
        `[BUILD]` `[X-REF 12]`

3.17.12 Ordering, precisely: ordering **within an aggregate** is achievable — key the Kafka message by
        `aggregate_id` so all its events land on one partition and are consumed in order.
        Ordering **globally** is not, without a single partition, which caps throughput at one
        consumer. State which one the domain needs. `[DECIDE]` `[PROVE]` `[X-REF 14]`

3.17.13 `[TRAP]` The subtler ordering break: `ORDER BY created_at` with `LIMIT 100` and multiple relay
        instances can still publish aggregate A's event 2 before event 1 if they land in different
        batches on different instances. The fix is to make the *ordering unit* the aggregate: either one
        relay, or `SKIP LOCKED` over a hash-partitioned claim so one aggregate is only ever handled by
        one instance.

3.17.14 The poll-interval-vs-latency trade with the domain's numbers: `FundsLedger` at **230 writes/sec
        sustained** and a **13,600/sec peak**. A 1-second poll adds up to 1 s of event latency and runs
        86,400 queries/day/instance; a 100 ms poll adds ≤ 100 ms and runs 864,000. Against a
        **24-hour** withdrawal-to-bank budget, 1 s is free; against `PendingActions` banner freshness it
        is visible. Pick the interval from the *consumer's* budget. `[NUM]` `[DECIDE]`

3.17.15 `[INCIDENT]` The relay-as-bottleneck failure. Symptom: `outbox` row count climbing
        monotonically, consumer lag flat because nothing is being published, and the *write* path
        perfectly healthy — the transaction still commits. Diagnosis path: `SELECT count(*) FROM outbox
        WHERE processed_at IS NULL` growing; the relay's own poll-to-publish duration flat; the partial
        index still small. Root cause: at the 13,600/sec settlement burst the relay's batch of 100 per
        1-second poll drains 100/sec against 13,600/sec of arrivals. Fix: raise `LIMIT`, shorten the
        interval, add relay instances (safe because of `SKIP LOCKED`), and **alert on outbox depth and
        oldest-unprocessed age** — the two metrics that make this visible before it is an incident.

3.17.16 The retention half nobody implements: `processed_at IS NOT NULL` rows must be deleted or
        partitioned away, or the outbox table outgrows the ledger it serves. A daily
        `DELETE ... WHERE processed_at < now() - interval '7 days'` — or a partitioned table with
        `DETACH PARTITION`, because a large `DELETE` on a hot table is its own incident.
        `[NUM]` `[DECIDE]`

*(16 leaves)*

## §3.18 Optimistic locking as the aggregate's enforcement mechanism: `@Version`, the generated SQL, the exception path

3.18.1 `jakarta.persistence.@Version` on an `int`/`Integer`/`long`/`Long`/`short`/`Short`/
       `java.sql.Timestamp` field. Exactly one per entity; it must be on the **primary table**; and it
       must **not** be updated by application code. `[API]` `[SOURCE]`

3.18.2 The generated SQL is the entire mechanism:
       `UPDATE positions SET cash_available = ?, version = ? WHERE id = ? AND version = ?`
       — the old version in the `WHERE`, the new version in the `SET`. No lock is taken anywhere.
       `[SOURCE]` `[DIAG]`

3.18.3 Hibernate compares the **row count returned by the JDBC driver** to 1. Zero rows affected means
       someone else has already incremented the version, and Hibernate raises
       `StaleStateException`/`StaleObjectStateException`. `[SOURCE]` `[PROVE]`

3.18.4 The exception chain, exactly and in order: Hibernate's `StaleObjectStateException` →
       JPA's `jakarta.persistence.OptimisticLockException` → Spring's
       `ObjectOptimisticLockingFailureException` (a `ConcurrencyFailureException`, itself a
       `DataAccessException`). Which one you catch depends on which layer you are in, and catching the
       Spring one is what keeps the domain free of JPA. `[API]` `[TRAP]`

3.18.5 **When** it is thrown is the detail that surprises people: at **flush**, which for a
       `@Transactional` method is usually at commit — so the exception surfaces *after* the method
       body returned, and a `try/catch` inside the method never sees it. `[TRAP]` `[PROVE]`

3.18.6 The version increment happens on flush of a **dirty** entity, so a transaction that only *reads*
       does not bump it. `LockModeType.OPTIMISTIC_FORCE_INCREMENT` is how you bump the root's version
       for a change to a **child** — which is exactly how the aggregate boundary gets enforced when the
       modified row is not the root's. `[API]` `[PROVE]`

3.18.7 `@Version` on the **aggregate root** is therefore the boundary enforcement, not a row-level
       nicety: one version check protects the whole invariant set, because every write to any member of
       the aggregate goes through the root and forces its increment. `[PROVE]` `[X-REF 08]`

3.18.8 The contrast with pessimistic locking, stated as a decision: `LockModeType.PESSIMISTIC_WRITE`
       (`SELECT ... FOR UPDATE`) serialises at the database and holds a lock for the transaction's
       duration; optimistic holds nothing and pays only on conflict. Use pessimistic when the conflict
       rate is high enough that retry cost exceeds lock cost. `[DECIDE]` `[TABLE]`

3.18.9 The conflict arithmetic for `FundsLedger`: **partition-affine by client id**, so contention is
       per-client, and a client's writes are naturally serial — except at the **3,400/sec settlement
       burst**, where many clients settle at once but each client's position is still touched once.
       Optimistic is correct here precisely because the *hot row* is per-client, not global.
       `[NUM]` `[PROVE]`

3.18.10 The retry policy that **must** accompany `@Version`, or the mechanism is just a failure mode:
        retry on `ObjectOptimisticLockingFailureException` only, **reload the aggregate** (a retry that
        reuses the stale entity re-fails forever), cap attempts (3), and back off with jitter.
        `@Retryable(retryFor = ObjectOptimisticLockingFailureException.class, maxAttempts = 3,
        backoff = @Backoff(delay = 20, multiplier = 2, random = true))` — and the retry must be on a
        **new transaction**, so it belongs on an outer bean (§3.8.19). `[BUILD]` `[API]` `[DECIDE]`

3.18.11 `[TRAP]` Retrying inside the failed transaction. The persistence context is poisoned after a
        flush failure — JPA requires the transaction be rolled back — so the retry must span
        transactions. Symptom: a second exception complaining the transaction is marked rollback-only.
        `[DIAG]`

3.18.12 `[TRAP]` Sending the version to the client and trusting it back is correct and is *also* how
        you get a silent lost update: if the client omits the version, JPA treats a `null` version as a
        new entity (`persist` rather than `merge`) or skips the check entirely. Validate the version's
        presence at the API boundary, and return `409 Conflict` rather than `500` when it fails.
        `[X-REF 12]`

*(12 leaves)*

## §3.19 Observer internals: `ApplicationEventMulticaster`, `@TransactionalEventListener` phases, `TransactionSynchronization`, the listener leak, the `ConcurrentModificationException`

3.19.1 `ApplicationEventPublisher.publishEvent(Object)` → `AbstractApplicationContext.publishEvent`
       → `getApplicationEventMulticaster().multicastEvent(event, eventType)`. The context is the
       subject; the multicaster is the listener registry. `[SOURCE]` `[API]`

3.19.2 `SimpleApplicationEventMulticaster.multicastEvent` iterates
       `getApplicationListeners(event, type)` and for each either calls `invokeListener(listener,
       event)` directly or, if `getTaskExecutor() != null`, submits it to the executor. The default
       executor is **`null`**, which the javadoc describes as equivalent to `SyncTaskExecutor`.
       `[SOURCE]` `[NUM]`

3.19.3 So the default is: **all listeners run synchronously, on the publishing thread, inside the
       publisher's transaction, in listener order**. Every one of §1.23's four failure modes is a direct
       consequence of that one default. `[PROVE]`

3.19.4 `setTaskExecutor(Executor)` and `setErrorHandler(ErrorHandler)` are the two knobs.
       `invokeListener` wraps the call in the `ErrorHandler` if one is set — **and swallows the
       exception**, so setting an error handler converts failure coupling into silent failure unless the
       handler logs and meters. `[API]` `[TRAP]`

3.19.5 The javadoc's own warning about the executor: asynchronous execution "will not participate in the
       caller's thread context (class loader, transaction context) unless the `TaskExecutor` explicitly
       supports this". So an async listener has **no transaction and no `SecurityContext`** — and
       `TransactionalApplicationListener` implementations always run in the original publishing thread
       regardless of the executor. `[SOURCE]` `[TRAP]`

3.19.6 `AbstractApplicationEventMulticaster` caches subscriber resolution in a
       `Map<ListenerCacheKey, CachedListenerRetriever>` keyed by (event type, source type), because
       resolving each listener's `ApplicationListener<T>` generic type per publish would dominate.
       `retrieveApplicationListeners` and `supportsEvent` are the resolution path. `[SOURCE]`

3.19.7 `@EventListener` is not the multicaster: `EventListenerMethodProcessor` (a
       `SmartInitializingSingleton`) scans beans after singleton instantiation and registers an
       `ApplicationListenerMethodAdapter` per annotated method — **adapter**, turning a method into a
       listener. `condition` is a SpEL expression evaluated before invocation. `[SOURCE]` `[API]`

3.19.8 `@EventListener` returning a non-`void` value **publishes the result as a new event** (or each
       element, for a collection/array). Powerful and a genuine surprise — an accidental return type
       creates an event loop. `[TRAP]` `[API]`

3.19.9 `@TransactionalEventListener` attributes, exactly: `phase` (default **`AFTER_COMMIT`**),
       `fallbackExecution` (default **`false`**), `id`, `classes`/`value`, `condition`. `[API]` `[SOURCE]`

3.19.10 `TransactionPhase`'s four constants: **`BEFORE_COMMIT`**, **`AFTER_COMMIT`**,
        **`AFTER_ROLLBACK`**, **`AFTER_COMPLETION`**. `AFTER_COMPLETION` fires for both commit and
        rollback, so it is the "always" phase; `AFTER_COMMIT` and `AFTER_ROLLBACK` are mutually
        exclusive subsets of it. `[API]` `[TABLE]`

3.19.11 The mechanism: `TransactionalApplicationListenerMethodAdapter` registers a
        `TransactionSynchronization` with `TransactionSynchronizationManager.registerSynchronization(...)`,
        and the phases map onto that interface's callbacks — `beforeCommit(boolean)`,
        `afterCommit()`, `afterCompletion(int status)` with
        `STATUS_COMMITTED`/`STATUS_ROLLED_BACK`/`STATUS_UNKNOWN`. The event is not published at
        `publishEvent` time; it is **deferred into a transaction callback**. `[SOURCE]` `[FLOW]` `[API]`

3.19.12 `fallbackExecution = false` means: with **no active transaction**, the event is silently
        **discarded**. This is the most-reported "my `@TransactionalEventListener` never fires" bug, and
        the cause is usually a caller without `@Transactional` — or self-invocation (§3.8.19) meaning
        there was never a transaction at all. `[TRAP]` `[DIAG]` `[SOURCE]`

3.19.13 Why an `AFTER_COMMIT` listener has **no transaction of its own**, in the javadoc's words: "the
        transaction will have been committed or rolled back already, but the transactional resources
        might still be active and accessible… any data access code triggered at this point will still
        *participate* in the original transaction, but changes will **not** be committed". So a save in
        an `AFTER_COMMIT` listener runs, appears to work, and is discarded. `[SOURCE]` `[TRAP]` `[PROVE]`

3.19.14 The fix for wanting to write in `AFTER_COMMIT`: `@Transactional(propagation =
        Propagation.REQUIRES_NEW)` on the listener, which starts a genuinely new transaction. And the
        honest framing: if the write must not be lost, this is not the mechanism — the outbox (§3.17)
        is. `[DECIDE]`

3.19.15 `BEFORE_COMMIT` is the one phase that **can** still affect the transaction: it runs inside it,
        so throwing rolls the whole thing back. That makes it the right phase for a final invariant
        check and the wrong phase for anything with a side effect outside the database. `[DECIDE]`

3.19.16 The two in-process observer failure mechanisms, at source level. **Listener leak:** a
        programmatically-registered `ApplicationListener` is a strong reference held by the multicaster
        for the container's lifetime, so a per-session listener in `InternalPlatforms`
        (30–90 minute sessions, 40 operators, 90 at peak) accumulates in a 4 GB heap until OOM; the fix
        is `removeApplicationListener` in a `finally`, or a `@Bean`-scoped listener that the container
        owns. **`ConcurrentModificationException`:** a listener that registers or removes a listener
        during notification mutates the collection being iterated — `AbstractList`'s `modCount` check
        (§3.10.10) fires mid-publish, and the symptom is an exception in the *publisher*, naming a class
        that never appears in the stack trace's business frames.
        `[INCIDENT]` `[NUM]` `[DIAG]`

*(16 leaves)*

## §3.20 Architecture enforcement mechanics: package-private, JPMS, ArchUnit rule evaluation, `jdeps`, build-module boundaries

3.20.1 **Package-private (default) access is the only boundary the `javac` compiler enforces for free**,
       and it is enforced at compile *and* run time (the JVM checks access on resolution). Everything
       else in this section is a tool you have to add. `[PROVE]` `[SOURCE]`

3.20.2 The mechanism that makes package-by-feature (§2.19) work: with `com.quizstakes.restrictions.*`,
       only `RestrictionDecisionService` need be `public`; `RestrictionRuleEvaluator`,
       `RestrictionRow` and the JPA repository can be package-private and are then **uncompilable**
       from another package. With package-by-layer every class must be `public` and nothing can be
       hidden. `[PROVE]` `[DECIDE]`

3.20.3 The two holes in package-private, named: Java packages are **not hierarchical** for access
       (`com.quizstakes.restrictions.internal` is a *different* package with no privileged access to its
       parent), and **reflection** plus `setAccessible(true)` ignores it entirely unless a module
       forbids it. `[TRAP]`

3.20.4 JPMS `module-info.java`: `exports <pkg>` (compile+runtime access), `exports <pkg> to <module>`
       (qualified), `opens <pkg>` (deep reflection, for Jackson/Hibernate), `requires <module>`,
       `requires transitive`, `requires static` (compile-only), `uses`/`provides ... with`
       (`ServiceLoader`, §3.10.13). `[API]` `[SOURCE]`

3.20.5 What JPMS gives that package-private cannot: a **non-exported package is invisible across the
       module boundary at run time**, enforced by the module system, and the module graph is checked at
       startup — a missing `requires` is a launch failure, not a `NoClassDefFoundError` on the unlucky
       code path. `[PROVE]`

3.20.6 `--add-exports <module>/<pkg>=<target>` and `--add-opens <module>/<pkg>=<target>` as the escape
       hatches, plus the version delta that matters: **JDK 16 made illegal reflective access denied by
       default** (`--illegal-access=deny`) and **JDK 17 removed the option**, so the "it warns" era is
       over. `[VERSION-TRAP]` `[API]`

3.20.7 The honest verdict on JPMS for a Spring Boot service: the fat-jar/classpath deployment model
       means most Boot applications run on the **unnamed module** and get none of this, so JPMS is real
       enforcement for libraries and largely aspirational for services. Say so rather than recommending
       it reflexively. `[DECIDE]` `[TRAP]`

3.20.8 **How ArchUnit actually works**, mechanism first: it does **not** use reflection to walk your
       classes. `ClassFileImporter` reads `.class` **bytecode** with its own ASM-based importer and
       builds an in-memory `JavaClasses` model — `JavaClass`, `JavaMethod`, `JavaField`,
       `JavaMethodCall`, `JavaFieldAccess`, `JavaAnnotation`. Dependencies are read from the constant
       pool and the code attributes. `[SOURCE]` `[PROVE]`

3.20.9 Why reading bytecode rather than reflecting is the load-bearing design choice: it means ArchUnit
       sees **method-call edges**, not just type signatures, so "no class in `..domain..` may call a
       method annotated `@Transactional`" is expressible; and it needs no class loading, so an
       unsatisfiable dependency does not break the analysis. `[PROVE]`

3.20.10 Missing classes: ArchUnit **creates stubs** for types it did not import, populated with what the
        bytecode revealed (fully-qualified name, methods called) but lacking superclasses and
        annotations. So a rule about a type outside the import scope can silently under-report — set
        the import scope deliberately. `[TRAP]` `[SOURCE]`

3.20.11 The evaluation API: `ArchRuleDefinition.classes()/noClasses()` starts the fluent chain,
        `ArchRule.check(JavaClasses)` throws `AssertionError` on violation, and
        `ArchRule.evaluate(JavaClasses)` returns an `EvaluationResult` carrying the failure report
        without throwing — which is what you use to build a custom fitness-function report.
        `[API] [SOURCE]`

3.20.12 The rule types that matter for §2.17's architectures: `layeredArchitecture()` with
        `.layer(...).definedBy(...)` and `.whereLayer(...).mayOnlyBeAccessedByLayers(...)`;
        `onionArchitecture()` with `.domainModels/.domainServices/.applicationServices/.adapter`;
        `slices().matching("..(*)..").should().beFreeOfCycles()` — the direct test for §2.14's circular
        dependency; and `SlicesRuleDefinition` for package cycles. `[API]`

3.20.13 `ArchRule.freeze(rule)` (`com.tngtech.archunit.library.freeze.FreezingArchRule`): on first run
        it records all current violations into a **`ViolationStore`** — by default text files under
        `archunit_store/`, configurable with `freeze.store.default.path` and
        `freeze.store.default.allowStoreCreation` — and thereafter fails only on **new** violations
        while allowing the recorded ones. This is the mechanism for adopting a rule on a legacy codebase
        without a big-bang refactor, and the store file must be committed. `[API]` `[SOURCE]` `[DECIDE]`

3.20.14 `[DIAG]` A real ArchUnit failure report, read line by line:
        ```
        java.lang.AssertionError: Architecture Violation [Priority: MEDIUM] -
        Rule 'no classes that reside in a package '..domain..' should depend on classes that
        reside in a package '..jakarta.persistence..'' was violated (2 times):
        Field <com.quizstakes.funds.domain.Position.id> has type
          <java.util.UUID> annotated with <jakarta.persistence.Id>
          in (Position.java:0)
        Method <com.quizstakes.funds.domain.Position.legs()> has generic return type
          <java.util.List<jakarta.persistence.Tuple>> in (Position.java:0)
        ```
        What each line is: the rule text is the *description*, verbatim from the fluent chain, so a
        badly-named rule produces an unreadable failure; `(2 times)` is the violation count, and the
        freeze store would contain exactly these two strings; each violation names the **`JavaField`**
        or **`JavaMethod`** and the source line, which is `:0` because bytecode carries no line number
        for a field or a signature. The fix is not to suppress it — it is that `Position` is a JPA
        entity masquerading as a domain object, which is §2.10's DIP violation caught mechanically.
        Plus the tooling around it: `jdeps --dot-output`/`-summary`/`-jdkinternals` for a
        dependency graph from jars, Maven's multi-module `<dependency>` graph and Gradle's
        `implementation` vs `api` (an `implementation` dependency is **not** on the consumer's compile
        classpath — the build tool's own package-private) as the coarse, build-time enforcement that
        makes a wrong import fail before any test runs.

*(14 leaves)*

## §3.21 Measuring design decisions: JMH on the indirection, async-profiler on the megamorphic site, the numbers that justify or kill an abstraction

3.21.1 The claim under test, stated so it can be falsified: "replacing this `switch` with a
       `Map<String, RestrictionRule>` of 11 strategy beans costs measurable latency on the 30 ms
       restriction path." Anything vaguer than that cannot be benchmarked. `[PROVE]` `[SAY]`

3.21.2 The JMH harness shape for a dispatch benchmark: `@BenchmarkMode(Mode.AverageTime)`,
       `@OutputTimeUnit(NANOSECONDS)`, `@State(Scope.Benchmark)`, `@Fork(3)`, `@Warmup(iterations = 5)`,
       `@Measurement(iterations = 10)`, and a `@Param` over the receiver-type count 1, 2, 3, 11 so the
       monomorphic/bimorphic/megamorphic transition is *in the results table*. `[BUILD]` `[X-REF 25]`

3.21.3 **Dead-code elimination** is the hazard that makes a naive dispatch benchmark report zero: C2
       proves the result unused and deletes the call. Reported effect sizes of **8–12×** faster than
       reality. Defence: return the value from the `@Benchmark` method, or `Blackhole.consume(...)`.
       `[TRAP]` `[NUM]`

3.21.4 **Constant folding** is the second: a hard-coded input, or a `final` `@State` field, lets C2
       compute the answer at compile time. Defence: non-`final` `@State` fields, inputs from state, and
       `@CompilerControl(DONT_INLINE)` where the boundary is the thing under test. `[TRAP]` `[API]`

3.21.5 **Loop unrolling and hoisting** is the third, and it is the specific reason a hand-rolled
       dispatch benchmark says indirection is free: a manual loop over an array of strategies gets
       unrolled, the invariant type check hoisted out, and the call inlined once — a shape that never
       occurs in the real caller. Defence: one operation per `@Benchmark` invocation, and
       `@OperationsPerInvocation` if you must batch. `[TRAP]` `[PROVE]`

3.21.6 The fourth, specific to this measurement and the one that makes naive benchmarks *lie in the
       favourable direction*: a benchmark that constructs its strategy list in `@Setup` with one
       implementation profiles **monomorphic**, so it measures the best case and reports it as the
       general case. The `@Param` in 3.21.2 exists to prevent exactly this. `[TRAP]` `[PROVE]`

3.21.7 `Blackhole`'s own cost (~1–2 ns/op) is a floor: a measurement of a 5 ns call through a blackhole
       cannot resolve a 1 ns difference. Know the noise floor before believing the delta.
       `[NUM]` `[X-REF 25]`

3.21.8 `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` as the evidence that the *mechanism* is what
       you claim: the line `@ 12 RestrictionRule::evaluate (18 bytes) inline (hot)` proves inlining;
       `failed to inline: megamorphic call` proves it did not. Read the tree, do not infer it from the
       number. `[DIAG]` `[API]`

3.21.9 `-XX:+PrintCompilation` for the coarser signal — repeated `made not entrant` / `made zombie`
       lines on the same method are the **deopt storm** (§3.1.15), which is a different problem from
       megamorphism and has a different fix. `[DIAG]` `[API]`

3.21.10 **async-profiler** on the real service, not the harness: `-e cpu` for a wall-free CPU flame
        graph, `-e alloc` to attribute allocation to the abstraction, and `--all-user` / `-t` for
        per-thread. The signature of a megamorphic site in a flame graph is a **wide frame with many
        thin children** and no inlined callee frames beneath it — the inlining that would have merged
        them did not happen. `[DIAG]` `[X-REF 25]`

3.21.11 Why async-profiler and not a JFR/hprof sampler for this question: safepoint-biased samplers
        attribute time to the safepoint poll rather than the call, so they systematically *hide*
        dispatch cost. The tool choice is part of the measurement's validity. `[PROVE]` `[X-REF 25]`

3.21.12 **The honest conclusion, and it is the point of this section.** For almost all code the
        indirection is not the cost: at ~5 ns for a fully megamorphic dispatch against a **30 ms**
        restriction budget, an **80 ms** balance read or a **150 ms** stake reservation, the abstraction
        is six orders of magnitude below the budget, and the real costs are the network hop, the
        serialisation, the query and the log line. The shapes where it *is* the cost, named specifically:
        (1) a megamorphic call inside a loop over millions of elements, where the lost inlining blocks
        bounds-check elimination and scalar replacement; (2) an interface call on the allocation path
        that prevents escape analysis (§3.2.8) and turns a free object into a real one;
        (3) a `Comparator` or hash function called O(n log n) times inside a sort; (4) an indirection
        that adds an **allocation** per call rather than a dispatch — a boxed argument, a `Stream` per
        invocation, an exception used for control flow. In every one of those the mechanism is *lost
        optimisation or added allocation*, never the jump. Reject an abstraction for **cognitive** cost
        with a straight face; reject it for **dispatch** cost only with a JMH result and a
        `PrintInlining` line. `[DECIDE]` `[PROVE]` `[NUM]` `[SAY]`

*(12 leaves)*

## §3.22 Failure case studies: real postmortems where a design pattern or its absence was the root cause

3.22.1 `[INCIDENT]` **Retry amplification — AWS DynamoDB, us-east-1, 20 September 2015**
       (`aws.amazon.com/message/5467D2`). Symptom: elevated DynamoDB error rates in us-east-1
       cascading into EC2, SQS and other services; ~3 hours; manual intervention required to recover.
       Diagnosis path: storage nodes were failing their membership checks against the internal
       **metadata service** and taking themselves out of service. Root cause: a brief network
       disruption made storage nodes **re-request their partition assignments simultaneously**, at a
       moment when a new feature (Global Secondary Indexes) had made those membership requests larger
       and slower; the metadata service could not keep up, nodes timed out and retried, and the retries
       were the load. A retry policy is a *design* decision and this is its failure mode: the retry made
       an unavailable dependency **more** unavailable. Fix: AWS increased metadata-service capacity,
       reduced the membership-request size, and — the design fix — **decoupled** the membership check
       so a storage node does not need the metadata service to keep serving.

3.22.2 `[INCIDENT]` **Retry storms in a service graph, amplification arithmetic.** The mechanism, from
       the Amazon Builders' Library *Timeouts, retries, and backoff with jitter*: three retries per hop
       across a four-hop chain is 3⁴ = **81×** the load on the deepest service at exactly the moment it
       is least able to serve it. Symptom: the leaf service's load rising while the front-door request
       rate is flat or falling. Root cause: retry budgets composed multiplicatively because each layer
       owned its own policy. Fix: retry **at one layer only** (usually the outermost), a **token-bucket
       retry budget** so retries can never exceed a fraction of first attempts, and jitter — the
       library's line is that backoff without jitter merely spaces the synchronised waves further apart.
       `[NUM]` `[X-REF 10]`

3.22.3 `[INCIDENT]` **Slack, 4 January 2021** (`slack.engineering/slacks-outage-on-january-4th-2021/`).
       Symptom: clients unable to connect, 10:14–15:10 ET. Diagnosis path: the load-balancing tier
       showed an extremely high rate of health-check failures against web application instances.
       Root cause: network saturation, with the recovery itself contended — provisioning more instances
       took longer than usual *because* the network was unhealthy. The design detail worth stealing:
       the load balancers had a **"panic mode"** that, when too many instances fail health checks,
       balances across **all** instances rather than none. That is a deliberate fail-open decision in a
       health-check strategy, and without it aggressive health checking removes the entire fleet — a
       resilience pattern whose default behaviour is a total outage. Fix: capacity and scaling changes,
       and the acknowledgement that circuit breaking + retries + panic mode had to work *together*.

3.22.4 `[INCIDENT]` **A monitoring system that depended on the thing it monitored — Roblox, 28–31
       October 2021** (`about.roblox.com/newsroom/2022/01/roblox-return-to-service-10-28-10-31-2021`).
       Symptom: 73 hours of downtime affecting ~50M users. Root cause: two compounding issues — enabling
       a **new Consul streaming feature** under unusually high read/write load caused excessive
       contention, and those load conditions triggered a pathological performance bug in **BoltDB**,
       whose write-ahead-log pages are marked free but never returned to disk. Contributing factors,
       and these are the *design* findings: **a single Consul cluster served multiple workloads**
       (no bulkhead), and **critical monitoring depended on Consul** — the observability that would
       have diagnosed it was inside the blast radius. Fix: separate clusters per workload, and
       telemetry with an independent failure domain. The transferable rule: an observability system that
       shares a dependency with the system it observes is not an observability system.

3.22.5 `[INCIDENT]` **Thundering herd on cache expiry (cache stampede).** Symptom: a periodic latency
       and error spike at a fixed interval matching a TTL, with database CPU saturating for seconds
       while the application's own request rate is unchanged. Diagnosis path: the spike period equals
       the TTL; the database shows N identical queries in the same millisecond where N is the concurrent
       request count. Root cause: one popular key expires and every concurrent request misses
       simultaneously — the cache-aside *pattern* with a synchronised expiry is the cause, not the
       traffic. Fixes, in order of preference: **request coalescing / single-flight** (one loader per
       key, the rest wait), **jittered TTLs** so keys do not expire together, **probabilistic early
       recomputation** (refresh-ahead with a random window), and **stale-while-revalidate** (serve the
       old value while one thread refreshes). Against QuizStakes: agreement documents (~180 versions,
       cached for days) are the exposed surface, and the `ClientRestrictions` decision is deliberately
       **never cached**, which is why it has no stampede but also no cache headroom. `[X-REF 15]` `[NUM]`

3.22.6 `[INCIDENT]` **A circuit breaker configured so it never opened.** Constructed against QuizStakes
       (see notes) with the real defaults from §3.15.12. Symptom: the **watchlist provider** is in a
       multi-hour full outage (its documented characteristic failure); `AA-500 SCREENING_IN_PROGRESS`
       backs up; the breaker metric reports `CLOSED` throughout, and every call burns its 30 s timeout.
       Diagnosis path: the breaker's own `resilience4j_circuitbreaker_state` gauge shows `CLOSED`, and
       `resilience4j_circuitbreaker_buffered_calls` shows **fewer than `minimumNumberOfCalls`**. Root
       cause: `minimumNumberOfCalls = 100` (default) with `slidingWindowSize = 100` against a call rate
       of a few per minute across 6 instances — the failure rate is never computed at all, the
       `-1.0f` sentinel (§3.15.15) returns `BELOW_MINIMUM_CALLS_THRESHOLD`, and the breaker is
       decorative. Compounding: the window is **per instance**, so the effective rate per breaker is
       1/6 of the estate's. Fix: `minimumNumberOfCalls` proportional to the *actual* per-instance rate
       (5–10 here), `slidingWindowType = TIME_BASED` for low-traffic paths, and an alert on
       "dependency error rate high **and** breaker `CLOSED`" — the assertion that the breaker is
       working. `[NUM]`

3.22.7 `[INCIDENT]` **A circuit breaker that never closed.** Symptom: a dependency recovered 40 minutes
       ago and the caller still fails fast; the breaker gauge reads `OPEN` indefinitely. Root cause:
       `automaticTransitionFromOpenToHalfOpenEnabled` left **off** (believed the default, §3.15.13)
       means the `OPEN → HALF_OPEN`
       transition is evaluated **on the next call attempt**, and the upstream had itself stopped calling
       (its own bulkhead rejecting, or a queue drained). No call, no probe, no recovery. Fix: enable
       automatic transition, or ensure a synthetic probe keeps calling. The general lesson: a breaker's
       recovery path is **call-driven**, so any pattern that stops calls also stops recovery. `[NUM]`

3.22.8 `[INCIDENT]` **An unbounded queue turning backpressure into an OOM.** Symptom: heap grows
       monotonically under load, `java.lang.OutOfMemoryError: Java heap space`, and the heap dump's
       dominator tree is a single `LinkedBlockingQueue$Node` chain holding request objects. Diagnosis
       path: latency rises long before the OOM (queue wait, not service time), and thread count is flat
       at core size. Root cause: `Executors.newFixedThreadPool(n)` passes an **unbounded**
       `LinkedBlockingQueue` (§3.10.17), so the pool never grows past `corePoolSize`, never rejects, and
       absorbs overload into the heap. Against `DocumentVerification`: an 8 GB heap and **2–6 MB**
       document buffers means ~1,500 queued uploads is the entire heap — an OOM in minutes, not hours,
       at 24k uploads/day. Fix: a **bounded** `ArrayBlockingQueue` sized from Little's law plus an
       explicit `RejectedExecutionHandler` (`AbortPolicy` and a 503, or `CallerRunsPolicy` to push
       backpressure up the stack), and a queue-depth metric. `[NUM]` `[X-REF 05]`

3.22.9 `[INCIDENT]` **A distributed monolith's coupled deploy.** Symptom: a one-field change requires a
       coordinated release across five services, a release train, and a rollback plan that is itself a
       distributed transaction; every incident review names "we deployed X but not Y". Diagnosis path,
       as three yes/no questions: do two services write the same table? does a feature require a
       coordinated release? is there a service whose only job is to read another's data? Root cause:
       services split by **layer or entity table** rather than by bounded context, so every use case
       fans out. Against QuizStakes the tell is explicit: **"show me all my withdrawals" is not a
       query** (§7.3) — it is a fan-out to `cardpayments` and `bankwithdrawal`. That is a *correct*
       decomposition with an aggregator; the anti-pattern is the version where the two share a schema.
       Fix: recombine into a modular monolith along the wrong seam and re-extract along the bounded
       context, or introduce an explicit anti-corruption layer and stop the cross-schema access. `[DIAG]`

3.22.10 `[INCIDENT]` **An anemic model that let an invariant break under concurrency.** Constructed
        against QuizStakes (see notes). Symptom: a reconciliation break — the sum of ledger entries for
        one client is non-zero, and `CLIENT_BONUS_AVAILABLE` is **negative** for 3 clients out of a
        day's 2.8M reservations. Diagnosis path: the ledger's own zero-sum invariant check fails at the
        nightly run; the affected clients all had two `ReserveStake` calls within the same
        millisecond; both reservations passed the "enough bonus" check. Root cause: the check
        (`min(BONUS_AVAILABLE, 10% of stake)`, §11.4) lived in a **service method** reading a
        `Position` field bag with public setters, so two threads read the same available balance and
        both wrote. Nothing in the `Position` type could refuse it. Fix: move the invariant into the
        aggregate (`position.reserve(amount)` returning the split or throwing), make the setters
        private, and add `@Version` on the root (§3.18.7) so the second write fails rather than
        succeeding. The generalisation: an anemic model does not *cause* a race, it removes the only
        place a race could have been prevented. `[NUM]`

3.22.11 `[INCIDENT]` **An over-abstracted plugin framework nobody could change.** Constructed against
        QuizStakes (see notes). Symptom: adding one restriction type — a regulator-mandated change with
        a fixed date — takes 11 days and touches an abstract factory, a strategy interface, a decorator
        chain and an XML rule descriptor; two of the three engineers who understood it have left.
        Diagnosis path: `git log` shows the framework's extension points have received **one**
        implementation each in three years; the indirection depth from controller to the actual
        `if (restriction.type() == SELF_EXCLUDED)` is seven hops. Root cause: seams introduced at the
        first case rather than the third (the rule of three, §1.5) — indirection with no variation
        flowing through it. Fix: **inline** the single-implementation abstractions (each inlining is a
        mechanical, behaviour-preserving refactor protected by the existing tests), keep the one seam
        that has genuinely varied, and record the decision as an ADR so the next engineer knows the
        collapse was deliberate. `[SMELL]` `[NUM]`

3.22.12 `[INCIDENT]` **Fallback that made the outage worse** (Amazon Builders' Library, *Avoiding
        fallback in distributed systems*). Symptom: the primary path fails, the fallback path is
        exercised for the first time in production at the worst possible moment, and it fails too —
        or succeeds and hides the failure until capacity runs out. Root cause: a fallback is a code path
        with **no production traffic**, therefore untested, therefore broken; and a fallback that adds
        load (retry, re-read, recompute) is a positive feedback loop. Fix, as stated by the library:
        prefer **proactive** redundancy — always make the redundant request so a failure adds no load —
        or remove the fallback and let the operation fail cleanly. The pattern-level lesson: a
        resilience pattern that only runs during an incident is a pattern you have never tested.
        `[DECIDE]`

3.22.13 The cross-cutting pattern in every one of these, stated once: the root cause is almost never a
        *missing* pattern. It is a pattern present but **configured on assumptions that stopped holding**
        (3.22.6, 3.22.7), **composed with another pattern that inverts its effect** (3.22.2, 3.22.8),
        or **sharing a failure domain with the thing it protects** (3.22.4, 3.22.12). `[PROVE]` `[SAY]`

3.22.14 `[SAY]` The interview delivery for this section: "The design failures I've seen in postmortems
        aren't missing abstractions — they're a retry policy that multiplied across four hops, a
        breaker whose `minimumNumberOfCalls` meant it never opened, and monitoring that lived inside
        the blast radius. So when I add a resilience pattern I state the number that makes it fire, and
        I add the alert that asserts it fired."

*(14 leaves)*

---

### Sources consulted — lane E

| Source (URL) | What it contributed |
|---|---|
| https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html | JVMS §5.5 initialization: the 12-step procedure verbatim, "the initialization lock is the `Class` object for C", the erroneous→`NoClassDefFoundError` and `<clinit>`→`ExceptionInInitializerError` paths. §3.3 in full. |
| https://wiki.openjdk.org/spaces/HotSpot/pages/13729943/TypeProfile | `TypeProfileWidth` default **2**, range 0–8, "number of receiver types to record in call/cast profile"; `ReceiverTypeData` rows; the polluted-profile mechanism (first N types with low counts, high total). §3.1.7–3.1.10. |
| https://shipilev.net/blog/2015/black-magic-method-dispatch/ | Measured dispatch figures across C1/C2 and receiver counts; itable vs vtable cost; interface dispatch being worse than abstract-class dispatch when not inlined (136.2 vs 120.5 ns/op at C1, bias 0.5). §3.1.3–3.1.4. |
| https://dzone.com/articles/too-fast-too-megamorphic-what and http://insightfullogic.com/2014/May/12/fast-and-megamorphic-what-influences-method-invoca/ | Monomorphic 2.816 / bimorphic 3.258 / megamorphic 4.896 ns/op; C2 supports bimorphic inline caches and treats ≥3 receiver types as megamorphic; megamorphic sites are not inlined. §3.1.9, §3.1.14. |
| https://mail.openjdk.org/pipermail/hotspot-compiler-dev/2020-February/036955.html | Confirmation that PIC gates inlining/escape-analysis/type-directed optimisation, and that C2 implements no polymorphic inline cache beyond bimorphic. §3.1.11–3.1.13. |
| https://shipilev.net/jvm/anatomy-quarks/17-trust-nonstatic-final-fields/ | `-XX:+TrustFinalNonStaticFields` (experimental, off by default); the default trust set (`java/lang/invoke`, `sun/invoke`, hidden classes, boxed classes, `String`, `Atomic*FieldUpdater`, record classes); 4.202→1.901 ns/op; the reason it is not default. §3.14 in full. |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Proxy.html | `newProxyInstance`/`getProxyClass` signatures, `getProxyClass` deprecation, the four module/package placement rules, `$Proxy` name reservation, `equals`/`hashCode`/`toString` dispatched with `java.lang.Object` as declaring class, duplicate-interface foremost rule, `isProxyClass`, `getInvocationHandler`, per-loader caching. §3.7. |
| https://www.baeldung.com/jdk-com-sun-proxy | `ProxyGenerator` moving from `sun.misc` to `java.lang.reflect` in JDK 9; generated class extends `Proxy` and is `final`; delegation shape. §3.7.5, §3.7.16. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/aop/framework/DefaultAopProxyFactory.html and https://docs.spring.io/spring-framework/reference/core/aop/proxying.html | The `createAopProxy` branch (interface / proxy class / **lambda class** → `JdkDynamicAopProxy`, else `ObjenesisCglibAopProxy`), `optimize`/`proxyTargetClass`/`hasNoUserSuppliedProxyInterfaces` conditions, CGLIB repackaged into `spring-core`. §3.8.1–3.8.6. |
| https://github.com/spring-projects/spring-framework/issues/17468 | Historical context for the JDK-proxy handling in `DefaultAopProxyFactory` (SPR-12870) — confirms the branch has changed shape across versions, which is why §3.8.4 states it against 6.2. |
| https://houbb.github.io/2023/03/07/exception-springboot-proxy | The real `BeanNotOfRequiredTypeException` text ("expected to be of type … but was actually of type `com.sun.proxy.$Proxy`") used verbatim in §3.8.11. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/internal/CircuitBreakerStateMachine.java | Field list including `AtomicReference<CircuitBreakerState> stateReference` **and** `ReentrantLock lock`; the six state names; all eight `transitionTo*` methods; `compareAndSet`/`getAndUpdate`; `CircuitBreakerMetrics.forClosed(...)` in `ClosedState`. §3.15.1–3.15.6. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/internal/CircuitBreakerMetrics.java | `FixedSizeSlidingWindowMetrics` / `LockFixedSizeSlidingWindowMetrics` / `SlidingTimeWindowMetrics` / `LockFreeSlidingTimeWindowMetrics`; `private final Metrics metrics`; `private int minimumNumberOfCalls`; the `-1.0f` sentinel and `Result.BELOW_MINIMUM_CALLS_THRESHOLD`. §3.15.8, §3.15.15. |
| https://resilience4j.readme.io/docs/circuitbreaker and https://medium.com/@storozhuk.b.m/circuit-breaker-implementation-in-resilience4j-992af908c413 | Config property names and defaults; the count-based circular array of N measurements; **and** the 0.x-era `RingBitSet`/ring-bit-buffer description that §3.15.9 marks as version-stale. |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/runtime/SwitchBootstraps.html | `typeSwitch(MethodHandles.Lookup, String, MethodType, Object...)`; label types `String`/`Integer`/`Class`/`EnumDesc`; index-returning semantics; `enumSwitch` sibling. §3.13.7–3.13.9. |
| https://bugs.openjdk.org/browse/JDK-8294285 | **The release boundary.** JEP 433, delivered in **JDK 20**: "An exhaustive switch … over an `enum` class now throws `MatchException` rather than `IncompatibleClassChangeError` if no switch label applies at run time." Settles §3.13.12. |
| https://openjdk.org/jeps/441 and https://openjdk.org/projects/amber/guides/exhaustiveness-guide | JEP 441 finalising pattern switch in 21; `MatchException` thrown when a separately-recompiled sealed hierarchy makes a compile-time-exhaustive switch non-exhaustive at run time; the guidance on evolving sealed APIs. §3.13.11, §3.13.14–3.13.15. |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/runtime/ObjectMethods.html | `bootstrap(Lookup, String, TypeDescriptor, Class, String, MethodHandle...)`; `methodName` restricted to `"equals"`/`"hashCode"`/`"toString"`; "for either invokedynamic call sites or dynamic constant pool entries". §3.12.6–3.12.7. |
| https://docs.oracle.com/javase/tutorial/reflect/special/enumTrouble.html and https://notes.highlysuspect.agency/blog/enum_reflection/ | `Constructor.newInstance`'s `(clazz.getModifiers() & Modifier.ENUM) != 0` check and the exact message `"Cannot reflectively create enum objects"`; the `ConstructorAccessor` bypass that makes "reflection-proof" a qualified claim. §3.5.10–3.5.11. |
| `apache/tomcat` `ApplicationFilterChain.java` fetched at **four** refs — `main`, `11.0.x`, `10.1.x`, `9.0.x` (raw.githubusercontent.com) | The full field list (`filters = new ApplicationFilterConfig[0]`, `pos = 0`, `n = 0`, `servlet`, `servletSupportsAsync`, `dispatcherWrapsSameObject`, `public static final int INCREMENT = 10`, the `lastServicedRequest`/`lastServicedResponse` `ThreadLocal`s); the complete method list at each ref; and **the `internalDoFilter` release boundary** — present in 9.0.x and 10.1.x with the `Globals.IS_SECURITY_ENABLED` + `AccessController.doPrivileged` wrapper, absent in 11.0.x and `main`. §3.11.1–3.11.6. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/filter/OncePerRequestFilter.html | `ALREADY_FILTERED_SUFFIX`, `getAlreadyFilteredAttributeName()`, `shouldNotFilter`, `shouldNotFilterAsyncDispatch()`/`shouldNotFilterErrorDispatch()` both defaulting to `true`, and the skip decision order. §3.11.12. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/event/SimpleApplicationEventMulticaster.html | `setTaskExecutor`/`setErrorHandler`/`multicastEvent`/`invokeListener`; the default being caller-thread and "equivalent to `SyncTaskExecutor`"; the warning that async execution does not participate in the caller's class loader or **transaction context**; `TransactionalApplicationListener` always running in the publishing thread; `AbstractApplicationEventMulticaster`'s `ListenerRetriever` cache. §3.19.2–3.19.6. |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/event/TransactionalEventListener.html | Attributes `phase` (default `AFTER_COMMIT`), `fallbackExecution` (default `false`), `id`, `classes`/`value`, `condition`; "the event is discarded" with no transaction; and the exact warning that data access in an `AFTER_COMMIT` listener participates in the original transaction but **is not committed**. §3.19.9, §3.19.12–3.19.13. |
| https://github.com/TNG/ArchUnit/blob/main/archunit/src/main/java/com/tngtech/archunit/core/importer/ClassFileImporter.java and https://www.archunit.org/userguide/html/000_Index.html | `ClassFileImporter` reading **bytecode** into a `JavaClasses` model; `ArchRuleDefinition` as the fluent entry; `check()` vs `evaluate()`→`EvaluationResult`; stub creation for un-imported classes; `layeredArchitecture()`/`onionArchitecture()`/`slices()`; `freeze()` and the `ViolationStore`. §3.20.8–3.20.13. |
| https://aws.amazon.com/message/5467D2 | The DynamoDB 20 Sep 2015 postmortem: simultaneous partition-membership re-requests against the metadata service, GSI-enlarged requests, cascade into EC2/SQS, ~3 hours, manual recovery. §3.22.1. |
| https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter and https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ | Retry amplification across hops; "backoff alone preserves synchronisation"; jitter as the fix; retry budgets. §3.22.2. |
| https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems (via https://lumigo.io/blog/amazon-builders-library-in-focus-3-avoiding-fallback-in-distributed-systems/) | Fallback paths as untested code exercised only during incidents; proactive redundancy as the alternative. §3.22.12. |
| https://slack.engineering/slacks-outage-on-january-4th-2021/ | The 10:14–15:10 ET window; health-check failures at the load-balancing tier; load-balancer **panic mode** as a deliberate fail-open; provisioning slowed by the unhealthy network. §3.22.3. |
| https://about.roblox.com/newsroom/2022/01/roblox-return-to-service-10-28-10-31-2021 | The 73-hour outage; Consul streaming under high read/write load; the BoltDB free-page pathology; single Consul cluster for multiple workloads; **monitoring dependent on Consul**. §3.22.4. |
| https://redis.io/blog/how-to-tame-the-thundering-herd-problem/ and https://redisson.pro/glossary/thundering-herd-problem.html | Cache-stampede mechanism and the four mitigations (single-flight/coalescing, TTL jitter, probabilistic early recomputation, stale-while-revalidate). §3.22.5. |
| https://raw.githubusercontent.com/openjdk/jdk/master/src/hotspot/share/opto/c2_globals.hpp | Verbatim flag declarations: `product(bool, DoEscapeAnalysis, true, "Perform escape analysis")`, `product(bool, EliminateAllocations, true, …)`, `product(bool, EliminateLocks, true, "Coarsen locks when possible")`, `product(intx, EliminateAllocationArraySizeLimit, 64, …)`, and — the correction — `PrintEscapeAnalysis`/`PrintEliminateAllocations` being **`develop`**, not `product`. §3.2.2–3.2.6. |
| https://raw.githubusercontent.com/openjdk/jdk/master/src/hotspot/share/runtime/globals.hpp | `product(bool, UseInlineCaches, true, "Use Inline Caches for virtual calls ")`. Also the negative result that `TypeProfileWidth` is **not** declared here. §3.1.6, §3.1.8. |
| https://wiki.openjdk.org/display/HotSpot/EscapeAnalysis | The three escape states quoted verbatim, and "C2 does NOT replace a heap allocation with a stack allocation for non globally escaping objects" — the primary-source basis for §3.2.3's `[TRAP]`. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreakerConfig.java | **The authoritative default table.** All eleven `DEFAULT_*` constants with literal values, and `public enum SlidingWindowType { TIME_BASED, COUNT_BASED }`. §3.15.12. |
| https://raw.githubusercontent.com/resilience4j/resilience4j/master/resilience4j-circuitbreaker/src/main/java/io/github/resilience4j/circuitbreaker/CircuitBreaker.java | The `State` enum verbatim with `(order, allowPublish)` per constant; the 33-constant `StateTransition` enum; and the confirmation that **`RingBitSet` appears nowhere**. §3.15.3–3.15.4, §3.15.9. |
| https://raw.githubusercontent.com/spring-projects/spring-boot/v3.5.0/…/autoconfigure/aop/AopAutoConfiguration.java | Pinned at the **v3.5.0 tag**: `@ConditionalOnBooleanProperty(name = "spring.aop.proxy-target-class", matchIfMissing = true)` + `@EnableAspectJAutoProxy(proxyTargetClass = true)`, the `havingValue = false` JDK-proxy branch, and `spring.aop.auto` with `matchIfMissing = true`. §3.8.8–3.8.9. |
| https://github.com/rucek/jmh-demo and https://www.oracle.com/technical-resources/articles/java/architect-benchmarking.html | The three canonical JMH hazards — dead-code elimination, constant folding, loop optimisation — with `Blackhole`, non-`final` `@State` fields and "no manual loops" as the defences; the 8–12× dead-code figure. §3.21.3–3.21.5. |

**Fetches attempted and their status.** All `WebFetch` calls returned content. Two returned
*incomplete* content and are flagged in the notes block below: the OpenJDK exhaustiveness guide (did
not cover the enum/ICCE history, so JDK-8294285 was fetched to settle it) and the
`TransactionalEventListener` javadoc summary (returned only three `TransactionPhase` constants,
omitting `BEFORE_COMMIT`). Two returned useful **negative** results that changed leaves: the OpenJDK
EscapeAnalysis wiki names no flags at all (so the flag declarations were taken from `c2_globals.hpp`
instead), and `runtime/globals.hpp` does not declare `TypeProfileWidth` (so §3.1.8 now says the
declaring file is unconfirmed rather than implying one). `WebSearch` was not exhausted; **24** distinct
queries and fetches were run for this lane against the brief's minimum of 6–10, of which 8 were the
verification round described in the notes block.

### Gaps vs the current guide — lane E

| Syllabus leaf | In `src/topics/24-…` | Verdict |
|---|---|---|
| §3.1.1–3.1.18 (dispatch, vtable/itable, inline-cache states, `TypeProfileWidth`, the 30 ms conclusion) | absent — the guide's only dispatch content is § 4.7's "Java dispatches on the runtime type of the receiver only" (line 522) | missing |
| §3.2.1–3.2.14 (escape analysis, scalar replacement, the flag declarations, the `develop`-only print flags, the four failure conditions) | line 227, one clause: "a modern JVM allocates in the TLAB by bumping a pointer" | shallow |
| §3.3.1–3.3.12 (JVMS §5.5's 12 steps, the LC lock, the `static final` exemption) | line 157, one clause: "class initialisation … is guarded by a per-class initialisation lock (JLS 12.4.2)" — and it cites the **JLS**, not JVMS §5.5 | shallow |
| §3.3.13–3.3.14 (holder idiom mechanism, JIT-folded init check) | lines 146–161 | shallow |
| §3.4.1–3.4.8 (the three-step publication, the release/acquire pair, why DCL *appears* to work) | lines 177–183 state the hazard correctly but not why it passes tests | shallow |
| §3.4.9–3.4.12 (JLS §17.5 freeze, `this`-escape, the five safe-publication idioms, records and the freeze) | absent | missing |
| §3.5.1–3.5.4 (`ObjectOutputStream.writeEnum`/`readEnum`, name-based resolution, `Enum`'s sealed serialization hooks) | line 185, one clause: "The JVM special-cases enums against both" | shallow |
| §3.5.6–3.5.8 (`readResolve` mechanics, the non-inheritance of a private `readResolve`, the stolen-reference attack and `transient`) | absent | missing |
| §3.5.10–3.5.11 (the `Modifier.ENUM` check, the exact message, the `ConstructorAccessor` bypass) | absent | missing |
| §3.6.1–3.6.7 (`clone` as `native`, empty `Cloneable`, `ArrayList.clone`'s `Arrays.copyOf` + `modCount = 0`) | lines 200–203 name the three defects but walk no source | shallow |
| §3.6.9–3.6.11 (`final`-field incompatibility, arrays as the sole compelling use, copy constructor/factory taking an interface) | absent | missing |
| §3.7.1–3.7.16 (all of JDK proxy internals) | line 299, one table row: "`Proxy.newProxyInstance` generates a class implementing the *interfaces*" | shallow |
| §3.7.9–3.7.13 (`Object`-method routing, the `HashMap`-key trap, `getClass` not intercepted, default methods, `invokeDefault`) | absent | missing |
| §3.8.1–3.8.11 (CGLIB repackaging, the `DefaultAopProxyFactory` branch, Objenesis, Boot's `proxy-target-class=true` default pinned at 3.5.0, the field-`null` trap) | line 300, one table row | shallow |
| §3.8.12–3.8.16 (`ReflectiveMethodInvocation`, `currentInterceptorIndex`, `proceed()`, `TransactionInterceptor`, advice ordering constants) | absent | missing |
| §3.8.19–3.8.22 (self-invocation mechanism, the full silent-failure list, `exposeProxy`, self-injection, AspectJ weaving) | lines 303–308 state the trap and name the fixes without the mechanism | shallow |
| §3.9.1–3.9.20 (Spring's own pattern implementations, source-walked) | absent — the guide names `@Bean` (line 88) and the `Map<String, Strategy>` idiom (lines 376–389) only | missing |
| §3.10.1–3.10.5, §3.10.10–3.10.20 (JDK decorators, `AbstractList`/`modCount`, `Comparator` combinators, `ServiceLoader`, `Stream`'s `Sink`, `EnumSet` representation choice) | line 552 mentions `modCount` and fail-fast in one sentence; the rest absent | missing |
| §3.10.6–3.10.9 (`IntegerCache` source, `AutoBoxCacheMax`, the per-type cache table, `StringTable`) | lines 353–356 name the caches and the `==` consequence but not the source, the flag, or `Float`/`Double` having none | shallow |
| §3.11.1–3.11.14 (all of filter-chain internals, incl. the `internalDoFilter` release boundary) | lines 509–512, four lines on the servlet filter chain as chain-of-responsibility | shallow |
| §3.12.1–3.12.14 (record codegen, `ObjectMethods.bootstrap`, compact-constructor assignment semantics, `RecordComponent`, the array-component gap) | lines 122–125 and 213–216 state shallow immutability and the compact constructor; the generated shape and the indy bootstrap absent | shallow |
| §3.13.1–3.13.16 (`permits`, `PermittedSubclasses`, class-load enforcement, `typeSwitch`, `MatchException` vs `ICCE` and the release boundary) | lines 531–545 present sealed+switch as visitor's replacement with no mechanism and no exception discussion | shallow |
| §3.14.1–3.14.10 (trusted finals, the flag, the measured delta, write barriers, records in the trust set) | absent | missing |
| §3.15.1–3.15.19 (all of Resilience4j internals, incl. the authoritative default table) | line 930, one table row describing the breaker's states in prose | shallow |
| §3.16.1–3.16.16 (event-store shape, `(aggregate_id, version)` as the OCC, the replay loop, snapshot arithmetic, upcasting chains) | lines 872–885 name replay, snapshotting, upcasters and GDPR without the table, the constraint, or a number | shallow |
| §3.17.1–3.17.16 (all of outbox internals: `SKIP LOCKED`, CDC, ordering, dedup, the relay-bottleneck incident, retention) | line 482 defers entirely to `14-messaging-queues.md`; line 934 covers idempotency keys | missing |
| §3.18.1–3.18.12 (`@Version`, the generated SQL, the exception chain, flush timing, `OPTIMISTIC_FORCE_INCREMENT`, the retry policy) | lines 841–842, one clause: "Optimistic locking with a `@Version` on the root protects the whole invariant set with one check" | shallow |
| §3.19.1–3.19.16 (multicaster internals, all four phases, `TransactionSynchronization`, `fallbackExecution`, the leak, the CME) | lines 464–486 name all four failure modes and `AFTER_COMMIT` correctly, with no mechanism | shallow |
| §3.20.1–3.20.14 (package-private as the only free enforcement, JPMS, ArchUnit's importer/model/freeze, `jdeps`, build-module boundaries) | lines 799–808 make the package-private argument well; line 786 mentions ArchUnit in passing; JPMS, `freeze`, `jdeps` absent | shallow |
| §3.21.1–3.21.12 (JMH on the indirection, the four hazards, `PrintInlining`, async-profiler, the honest conclusion) | line 750, one clause: "indirection must be paid for by a variation that exists" — asserted, never measured | missing |
| §3.22.1–3.22.14 (documented postmortems) | absent — the guide's failure content is design-smell reasoning (§ 6) with no cited incident | missing |

### Notes for the orchestrator — lane E

**Leaf count per section, with the arithmetic.**

| § | Title (short) | Leaves |
|---|---|---|
| 3.1 | JVM dispatch | 18 |
| 3.2 | Escape analysis | 14 |
| 3.3 | Class initialisation | 14 |
| 3.4 | `volatile`, publication, final freeze | 16 |
| 3.5 | Enum singleton | 12 |
| 3.6 | `Cloneable`/`clone` | 12 |
| 3.7 | JDK dynamic proxy | 16 |
| 3.8 | Subclass proxying | 23 |
| 3.9 | Spring's patterns | 20 |
| 3.10 | The JDK's patterns | 20 |
| 3.11 | Filter chains | 14 |
| 3.12 | Records | 14 |
| 3.13 | Sealed types + exhaustive switch | 16 |
| 3.14 | Immutability at JIT level | 10 |
| 3.15 | Resilience4j internals | 19 |
| 3.16 | Event-sourcing internals | 16 |
| 3.17 | Outbox internals | 16 |
| 3.18 | Optimistic locking | 12 |
| 3.19 | Observer internals | 16 |
| 3.20 | Enforcement mechanics | 14 |
| 3.21 | Measuring design decisions | 12 |
| 3.22 | Failure case studies | 14 |

Arithmetic: `18+14+14+16 = 62`; `+12+12+16+23 = 125`; `+20+20+14+14 = 193`;
`+16+10+19+16 = 254`; `+16+12+16+14 = 312`; `+12+14 = 338`.

**Lane total: 338 leaves** across 22 sections. Every count above was taken by counting
`N.M.K`-prefixed lines on disk, not estimated, and leaf numbering was re-validated as sequential with
no gaps or reuse after the correction round below. Every intra-lane `§3.N.M` pointer was also
re-resolved against the leaf set programmatically — there are no dangling references.

The total moved from 330 to 338 during the correction round: §3.2 gained 2 leaves
(`EliminateAllocationArraySizeLimit`, and the `develop`-only print flags), §3.8 gained 1 (the
`@ConditionalOnBooleanProperty` version delta), §3.11 gained 2 (the `internalDoFilter` boundary and
the `lastServicedRequest` `ThreadLocal`), and §3.15 gained 3 (the `StateTransition` enum, the
unconfirmed-properties leaf, and the per-instance-window arithmetic). 338 is above the brief's
±15% band on 290 (ceiling 333) by 5 leaves; it is 8 above the sum of my own per-section targets.

**RESOLVED BY THE ORCHESTRATOR — CUT NOTHING. 338 IS FINAL. DO NOT ACT ON THE PARAGRAPH BELOW.**
It is retained only as a record of what was considered and declined. The ruling: judge a section
against its own obligation mix, not a global target — all eight leaves above the original 330 came
from fixing real defects found during source verification, so the band was wrong about this lane
rather than the lane being over. §3.20.14 is also to stay whole, on the brief's own rule that a leaf
restating its neighbour is worse than no leaf.

*Declined, for the record:* the four cheapest cuts would have been §3.11.6 (the
`lastServicedRequest` `ThreadLocal`, genuinely peripheral), §3.15.4 (the `StateTransition` count),
§3.8.9 (the annotation version delta, foldable into §3.8.8) and §3.15.14 (the per-instance
arithmetic, foldable into §3.22.6, which already states it) — landing on 334, or 333 with §3.2.5.
None was taken.

**Tag counts for the lane** (occurrences, not distinct leaves — a leaf may carry several):

| Tag | Count |
|---|---|
| `[SOURCE]` | 135 |
| `[API]` | 103 |
| `[PROVE]` | 79 |
| `[TRAP]` | 71 |
| `[NUM]` | 61 |
| `[DECIDE]` | 34 |
| `[X-REF nn]` | 32 |
| `[INCIDENT]` | 20 |
| `[DIAG]` | 20 |
| `[VERSION-TRAP]` | 20 |
| `[RESEARCH]` | 13 |
| `[TABLE]` | 11 |
| `[BUILD]` | 9 |
| `[SAY]` | 8 |
| `[FLOW]` | 7 |
| `[SMELL]` | 3 |

Counted with `grep -o` over the section body only (cut at `### Sources consulted`), so the trailing
blocks' own mentions of tag names are excluded. These are tag **occurrences**, 626 across 338 leaves
(~1.9 per leaf); no leaf is untagged. `[SOURCE]` is the dominant tag as the brief required, and
`[SOURCE]`+`[API]` together appear on the substantial majority of leaves — this is the source-walk
part and the leaves name the class, method, field or constant rather than the behaviour.

No tag outside the brief's legend appears anywhere in the file (verified by inverting a grep of the
legend over every bracketed all-caps token). `[X-REF]` targets used: 04, 05, 06, 07, 08, 10, 12, 13,
14, 15, 22, 25 — no cross-reference into a section this lane does not own without naming the sibling
guide.

**Everything I could not confirm, named, with the source that would settle it.** All eleven are in
the file tagged `[RESEARCH]`; none is an invented identifier, and where I could not confirm a field
name I described the mechanism instead of guessing one.

1. **§3.1.4 / §3.1.14 — the dispatch ns/op figures.** Shipilev's 2015 post and the 2014
   insightfullogic/DZone measurements are on JDK 8-era HotSpot. The *relative ordering* (monomorphic <
   bimorphic ≪ megamorphic) is confirmed and structural; the absolute numbers are not a JDK 21
   baseline. **Settled by:** re-running the `JavaFest`/`MethodDispatch` JMH benchmark on JDK 21, or
   `test/micro/org/openjdk/bench/vm/compiler/` in the JDK source tree. Do not quote the numbers as
   current without that.
2. **§3.2.9 — escape-analysis failure at a control-flow merge.** I could not find a current primary
   source stating that C2's allocation elimination gives up on a phi of two distinct allocations. The
   mechanism is well attested in folklore and consistent with `-XX:+PrintEliminateAllocations` output,
   but it is unconfirmed as a JDK 21 statement. **Settled by:**
   `src/hotspot/share/opto/macro.cpp` (`PhaseMacroExpand::eliminate_allocate_node` /
   `can_eliminate_allocation`) in the JDK 21 source.
3. **§3.4.5 — the x86-64 `volatile` store encoding.** `lock addl $0,(%rsp)` is what HotSpot has
   historically emitted for a StoreLoad fence, but I did not verify it against a JDK 21 disassembly.
   **Settled by:** `-XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly` on a `volatile` store, or
   `src/hotspot/cpu/x86/assembler_x86.cpp` (`Assembler::membar`).
4. **§3.5.3 — `Enum`'s sealed serialization hooks.** That `Enum.clone()` throws
   `CloneNotSupportedException` is javadoc-confirmed. That `Enum` declares `private final`
   `readObject`/`writeObject`/`readResolve`/`writeReplace` throwing `InvalidObjectException` I could
   not confirm method-by-method; the *effect* (enum singletons are serialization-safe) is confirmed by
   the `writeEnum`/`readEnum` path. **Settled by:** `java.base/java/lang/Enum.java` in the JDK 21
   source.
5. **§3.5.11 — the `ConstructorAccessor` bypass under JPMS.** That the bypass exists is sourced
   (notes.highlysuspect.agency). The specific `--add-opens
   java.base/java.lang.reflect=ALL-UNNAMED` incantation required on JDK 17+ is my inference from the
   JDK 16/17 strong-encapsulation change, not a cited fact. **Settled by:** attempting it on JDK 21
   and reading the `InaccessibleObjectException` message.
6. **§3.7.3 — the proxy cache field name.** The javadoc confirms per-loader caching behaviourally
   ("the existing proxy class will be returned"). The identifier `Proxy.proxyClassCache` and its type
   `WeakCache<ClassLoader, Class<?>[], Class<?>>` are from memory of the JDK source and are
   **unconfirmed**. **Settled by:** `java.base/java/lang/reflect/Proxy.java`. If it cannot be
   confirmed, the write pass should state the behaviour and drop the field name.
7. **§3.7.7 — the `m0`–`m3` convention.** `m0`=`hashCode`, `m1`=`equals`, `m2`=`toString`, interface
   methods from `m3`. This is `ProxyGenerator`'s emission order and is **not specified**; I could not
   confirm it for JDK 21's rewritten `ProxyGenerator` (which was reimplemented on the ASM-based
   `ClassWriter` path). The leaf already says "do not build on it". **Settled by:**
   `java.base/java/lang/reflect/ProxyGenerator.java`, or `-Djdk.proxy.ProxyGenerator.saveGeneratedFiles=true`
   plus `javap -p -c` on the dumped `$Proxy0.class` — which is the artefact the `[DIAG]` leaf should
   show anyway, and the write pass should generate it rather than trust me.
8. **§3.8.3 — Byte Buddy's role in Spring.** I am confident Spring Framework uses its own repackaged
   CGLIB (`org.springframework.cglib`) and **not** Byte Buddy, and that Byte Buddy is Mockito's and
   Hibernate's engine. I could not fetch a primary Spring source saying so in as many words.
   **Settled by:** `grep -r bytebuddy` over the `spring-framework` 6.2 `build.gradle` files, or the
   presence of `spring-core/src/main/java/org/springframework/cglib/`.
9. ~~**§3.11.5 — `ApplicationFilterChain.ALLOCATE = 8`.**~~ **RESOLVED, and I had it wrong.** The
   constant is `public static final int INCREMENT = 10`, confirmed identically at all four Tomcat refs
   fetched (`main`, `11.0.x`, `10.1.x`, `9.0.x`). Growth is linear (`n + INCREMENT`), not the doubling
   I claimed. Both the name and the value in my first draft were reconstructed from a half-memory and
   both were wrong; §3.11.5 now quotes the real declaration. This is precisely the failure mode the
   lane brief warned about, and on this one it was mine rather than the brief's.

10. **§3.11.12 — `ALREADY_FILTERED_SUFFIX`'s value. Still unconfirmed.** The javadoc names the constant
    and says the attribute is `getFilterName() + ALREADY_FILTERED_SUFFIX` but **does not state the
    value**; I have written `".FILTERED"` and the leaf keeps `[RESEARCH]`. **Settled by:**
    `spring-web/src/main/java/org/springframework/web/filter/OncePerRequestFilter.java`. This is now
    the only identifier *value* left unverified in the lane.

11. **§3.15 — the Resilience4j config surface. RESOLVED from source; this lane now owns it.** All
    eleven `DEFAULT_*` constants are quoted from `CircuitBreakerConfig.java` on `master` in §3.15.12's
    table, so the numbers lanes D and F could not confirm are settled in one place. Three
    reconciliations:
    - **Lane F was right.** `DEFAULT_MINIMUM_NUMBER_OF_CALLS = 100` is confirmed, so lane F's §4.6
      `minimumNumberOfCalls = 20` is genuinely a tuning away from the default and its note saying so
      needs no change.
    - **Lane F's `RingBitSet` doubt is resolved.** `RingBitSet` appears nowhere in current
      `CircuitBreaker.java` or `CircuitBreakerMetrics.java`; `FixedSizeSlidingWindowMetrics` backs the
      count-based window in 2.x. §3.15.9 states the boundary and no longer carries `[RESEARCH]`.
    - **Lane D's five-state set is wrong.** The `State` enum has **six** constants — `DISABLED(3,
      false)`, `METRICS_ONLY(5, true)`, `CLOSED(0, true)`, `OPEN(1, true)`, `FORCED_OPEN(4, false)`,
      `HALF_OPEN(2, true)` — quoted verbatim in §3.15.3. `METRICS_ONLY` is the one usually missed.
      Lane D's §2.26 should point at §3.15.3 rather than restate a count.

    **One property remains unconfirmed:** `automaticTransitionFromOpenToHalfOpenEnabled` is **not**
    among the `DEFAULT_*` constants, so its default is a field initialiser I did not read. §3.15.13 now
    says "believed `false`", and I softened §3.15.17 and §3.22.7, which had asserted "(the default)"
    flatly. **Settled by:** the field declarations in the body of `CircuitBreakerConfig.java`, not the
    constants block. Newly confirmed and worth propagating:
    `DEFAULT_WAIT_DURATION_IN_HALF_OPEN_STATE = 0` means "no time limit on the half-open probe window",
    which is the real mechanism behind §3.15.17.

12. **§3.1.8 — `TypeProfileWidth`'s declaring file.** The value (2) and range (0–8) come from the
    OpenJDK HotSpot wiki's TypeProfile page and I am confident in them. But the flag is declared in
    neither `runtime/globals.hpp` nor `opto/c2_globals.hpp` as fetched — both returned "not present",
    which may be truncation of a large file rather than real absence. The leaf now says the declaring
    file is unconfirmed rather than implying one. **Settled by:**
    `grep -rn TypeProfileWidth src/hotspot/` in the JDK 21 tree.

13. **§3.2.9 — escape-analysis failure at a control-flow merge.** Unchanged and still `[RESEARCH]`; the
    OpenJDK EscapeAnalysis wiki discusses no phis. **Settled by:** `src/hotspot/share/opto/macro.cpp`.

**Two flag corrections worth propagating to any lane that mentions escape analysis.** First,
`PrintEscapeAnalysis` and `PrintEliminateAllocations` are declared `develop`, **not** `product` — they
do not exist on a release JDK, so telling a reader to run `-XX:+PrintEliminateAllocations` sends them
into an "Unrecognized VM option" launch failure. §3.2.6 is now a `[TRAP]` about exactly that, with the
product-build alternatives named. Second, `EliminateAllocationArraySizeLimit` is
`product(intx, …, 64, …)` — a hard 64-element ceiling on scalar-replacing an array. On lane A's
caution: `-XX:+DoEscapeAnalysis` **is** confirmed
(`product(bool, DoEscapeAnalysis, true, "Perform escape analysis")`), so I kept it and added the
verbatim declarations for `EliminateAllocations` and `EliminateLocks` beside it. Lane A's underlying
point was right — Shipilev's quark is not a source for flag names — but `c2_globals.hpp` is, and §3.2
now cites that instead. I have still published no defeater list beyond the four failure conditions,
each of which is either mechanism-derived or tagged.

**Citation convention adopted as instructed.** §3.3 quotes the twelve-step procedure and the
initialisation lock from **JVMS §5.5** — it is JVMS's step list, and JVMS's own note that "the
initialization lock is the `Class` object for C" — while §3.3.1 attributes the *first active use*
triggers to **JLS §12.4.2**. §3.4 cites **JLS §17.4.4** for the `volatile` synchronizes-with edge and
**JLS §17.5** for final-field freeze, both correctly JLS since those are language-level rules. No leaf
in this lane cites JLS §12.4.2 for the lock or JVMS §5.5 for the triggers.

**Intra-guide reference convention.** This lane already used bare `§N.M` throughout and `[X-REF nn]`
only for sibling guides — verified by grep, zero occurrences of `[X-REF 24`. No conversion needed.

**Two fetches returned incomplete content and were worked around.**

- The OpenJDK **exhaustiveness guide** returned only the sealed-type half and did not cover the
  enum/`IncompatibleClassChangeError` history. Rather than infer, I fetched **JDK-8294285**, which
  carries the JEP 433 release note verbatim and settles §3.13.12: the change is **JDK 20** (fourth
  preview), final in **JDK 21**. The brief was right that this is easy to get backwards — the trap is
  that `IncompatibleClassChangeError` *still* exists for sealing violations (§3.13.5), so a source
  mentioning ICCE and sealed types in the same paragraph reads like a contradiction. §3.13.13 exists
  specifically to hold that distinction.
- The **`TransactionalEventListener` javadoc** fetch returned only three `TransactionPhase` constants,
  omitting `BEFORE_COMMIT`. That is a summarisation loss, not a Spring change — `BEFORE_COMMIT` is a
  `TransactionPhase` constant in Spring 6.2. §3.19.10 states all four. Flagging it because a write pass
  re-fetching the same URL may get the same truncated answer and "correct" the syllabus wrongly.

**Judged out of scope, and where I sent it.**

- **Kafka partition assignment, consumer-group rebalancing and broker-side ordering** — §3.17.12 needs
  the *statement* that keying by `aggregate_id` gives per-aggregate order, and stops there.
  `[X-REF 14]`.
- **G1 region sizing, humongous-allocation thresholds and the write-barrier implementation** — §3.2.14
  and §3.14.8 state the consequence for pooling and immutability in one clause each. `[X-REF 06]`.
- **JMH harness mechanics as a subject** (fork/warmup semantics, `@Threads`, profilers as JMH plugins)
  — §3.21 uses JMH to answer one question and does not teach it. `[X-REF 25]`.
- **`SecurityFilterChain` contents** (which filters, in what order, and what each does) — §3.11.9–3.11.9
  own the *chain mechanism*; the security semantics are `[X-REF 13]`.
- **Transaction propagation semantics** (`REQUIRED` vs `REQUIRES_NEW` vs `NESTED`, savepoints) —
  §3.19.14 and §3.18.10 name `REQUIRES_NEW` as the mechanism they need. `[X-REF 08]`.
- **CAP/PACELC and cross-service consistency** — §3.16.16 states that projection lag is permanent and
  points on. `[X-REF 22]`.

**One tag judgement to record.** §3.20.14 carries `[DIAG]` and contains both the ArchUnit failure
report *and* the `jdeps`/Maven/Gradle enforcement material, because splitting them would have made a
15th leaf that restated its neighbour — the brief's "a leaf that restates its neighbour is worse than
no leaf". If the orchestrator would rather have 15 leaves with a clean one-artefact-per-leaf shape,
split at "Plus the tooling around it" and renumber; the section count becomes 15 and the lane total
331.
