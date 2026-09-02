# Syllabus — 06 JVM Internals

**Target version: Java 21 LTS on 64-bit HotSpot (OpenJDK)** — the baseline for every constant,
flag default, header layout and collector behaviour below. Anything introduced, changed, removed or
promoted in Java 22–25 is marked inline with its release and, where it supersedes a Java 21
behaviour, with `[VERSION-TRAP]`. The four version deltas this topic carries most heavily are
**JEP 439 (Java 21): Generational ZGC**, **JEP 474 (Java 23): generational ZGC becomes the ZGC
default and the non-generational mode is removed in Java 24**, **JEP 450 → 519 → 534: compact
object headers, experimental in 24, product in 25, headed for default**, and **JEP 483 → 514/515:
the Leyden AOT cache, which changes the startup and warmup story that every older guide describes
in terms of CDS alone**.

Scope boundary against the sibling guides: the *language* semantics of `final`, `static`,
exceptions, generics erasure and the `String` pool live in `03-java-core.md`; the *user-facing*
concurrency API, the JMM as a programming contract, monitor semantics, `synchronized`/`volatile`
and virtual threads as an API live in `05-multithreading-concurrency.md`; the collection data
structures live in `02-java-collections.md`; OS-level process, paging, cgroup and signal mechanics
live in `11-operating-systems-linux.md`; container packaging and Kubernetes limits live in
`19-docker-kubernetes.md`; production metrics/tracing practice lives in
`20-observability-operations.md`. **This file owns the runtime**: the class file, the loader, the
verifier, the interpreter, the JIT, the object layout, the collectors, the memory subsystems
outside the heap, safepoints, startup, and the diagnostic toolchain. Where a concept is owned
elsewhere the leaf carries `[X-REF nn]` and the bible states the mechanism in one paragraph before
pointing away — it never sends the reader off empty-handed.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real JVMS/JLS text, HotSpot source or JEP text (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic Java 21 code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 21 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number / byte arithmetic explicitly |
| `[FLAG]` | must give the exact `-XX:` / `-X` flag spelling and its default value |
| `[BYTECODE]` | must show `javap -c` / `javap -v` output and read it instruction by instruction |
| `[DUMP]` | must show real `jcmd` / `jstack` / `-Xlog` / NMT / hs_err output and read it line by line |
| `[ASM]` | must show generated machine code or a barrier and read it instruction by instruction |

---

# PART 1 — BASICS

## §1.1 Why a virtual machine exists at all

1.1.1 The 1995 problem statement: ship one artifact that runs unmodified on every CPU and OS, with
      memory safety and no manual deallocation. "Write once, run anywhere" is an *architecture*
      decision, not marketing.
1.1.2 The three things the JVM buys you that a native binary does not: portability of the artifact,
      automatic memory management, and **profile-guided optimisation at runtime** — the last of
      which is the one people forget and the one that lets Java match C on long-running servers.
      `[PROVE]`
1.1.3 The three things it costs you: startup latency (class loading + warmup), memory footprint
      (heap + metadata + code cache + GC structures), and unpredictable pause behaviour.
1.1.4 The JVM is a *specification* (JVMS), not a program. HotSpot, OpenJ9, GraalVM, Azul Zing/Prime,
      Amazon Corretto and Zulu are implementations; only some behaviours in this file are
      JVMS-mandated and the rest are HotSpot-specific. Say which is which, always. `[TRAP]`
1.1.5 JDK vs JRE vs JVM, stated precisely: JVM = the execution engine; JRE = JVM + class library;
      JDK = JRE + tools (`javac`, `jcmd`, `jlink`, `jfr`). Since Java 11 there is no separate JRE
      download — `jlink` produces one instead. `[VERSION-TRAP]`
1.1.6 The three normative documents and which to cite: JVMS (class file, runtime, instruction set),
      JLS (language semantics, chapter 17 = memory model), API javadoc (library contract).
      `[X-REF 03]`
1.1.7 JVMS 21 chapter map so you know where an answer lives: 1 introduction, 2 structure of the JVM,
      3 compiling for the JVM, 4 the class file format, 5 loading/linking/initializing,
      6 the instruction set, 7 opcode mnemonics by opcode. `[SOURCE]` `[RESEARCH]`
1.1.8 The pipeline end to end, named at every arrow: `.java` → `javac` → `.class` → class loader →
      verifier → linker → interpreter → profile → C1 → C2 → machine code, with GC and safepoints
      running underneath the whole thing. Every later section is one arrow on this diagram.
1.1.9 What `javac` decides versus what the runtime decides — the line that answers most "why does
      Java do X" questions: constant folding, autoboxing, string concatenation strategy, generic
      erasure and overload *resolution* are compile time; null checks, virtual dispatch,
      initialisation order, inlining and allocation are runtime. `[X-REF 03]` `[TRAP]`
1.1.10 HotSpot's name comes from the "hot spot" detection idea: interpret everything, measure, and
       spend compilation budget only where it pays.
1.1.11 The two historical HotSpot VMs, `-client` (C1) and `-server` (C2), and why the distinction is
       gone: tiered compilation uses both, and `-client` is ignored on 64-bit. `[VERSION-TRAP]`
1.1.12 Why a *stack* machine and not a register machine: compact bytecode, trivial portability
       across register counts, easy verification — at the cost of needing a JIT to be fast.
       `[PROVE]`
1.1.13 The JVM as a polyglot runtime: Kotlin, Scala, Clojure, Groovy and Jython all emit class
       files, which is why `invokedynamic` and the class file format are language-neutral.
1.1.14 What "the JVM is slow to start" actually decomposes into, measurably: process exec, JVM
       init, class loading and verification of ~2000–6000 classes, static initialisers, and
       interpreted execution before the JIT catches up. Each has a different fix (§2.8). `[NUM]`
1.1.15 The interview framing this whole guide serves: turning "the service got slow and then died"
       into a diagnosis with named tools and named evidence.

*(15 leaves)*

## §1.2 The class file format

1.2.1 A class file is a single `ClassFile` structure of big-endian, unaligned, variable-length
      items — no padding, no alignment, and independent of the host byte order. `[SOURCE]`
1.2.2 `magic` = `0xCAFEBABE`, four bytes, the first thing every parser checks. `[NUM]` `[SOURCE]`
1.2.3 `minor_version` and `major_version`: the class file version table — 45 = 1.1, 46 = 1.2,
      47 = 1.3, 48 = 1.4, 49 = 5, 50 = 6, 51 = 7, 52 = 8, 53 = 9, 54 = 10, 55 = 11, 56 = 12,
      57 = 13, 58 = 14, 59 = 15, 60 = 16, 61 = 17, 62 = 18, 63 = 19, 64 = 20, **65 = 21**, 66 = 22,
      67 = 23, 68 = 24, 69 = 25. Major = 44 + Java version. `[NUM]` `[RESEARCH]`
1.2.4 `minor_version = 65535` marks a **preview-feature** class file, runnable only on exactly that
      release with `--enable-preview`. This is the mechanism behind "preview features are not
      binary compatible across releases". `[NUM]` `[RESEARCH]`
1.2.5 `UnsupportedClassVersionError: ... has been compiled by a more recent version of the Java
      Runtime (class file version 65.0), this version ... recognizes class file versions up to
      52.0` — read the two numbers, subtract 44, and you have both versions. `[TRAP]` `[NUM]`
1.2.6 `--release N` versus `-source`/`-target`: only `--release` also swaps the API signature set,
      so `-target 8` alone still lets you compile against Java 21 APIs that will fail at runtime
      with `NoSuchMethodError`. `[TRAP]` `[X-REF 03]`
1.2.7 `constant_pool_count` is *one more* than the number of entries, and the pool is indexed from
      1, not 0. Index 0 is reserved as "no entry". `[TRAP]` `[SOURCE]`
1.2.8 The constant pool tag inventory, every one by tag byte and name: 1 `CONSTANT_Utf8`,
      3 `Integer`, 4 `Float`, 5 `Long`, 6 `Double`, 7 `Class`, 8 `String`, 9 `Fieldref`,
      10 `Methodref`, 11 `InterfaceMethodref`, 12 `NameAndType`, 15 `MethodHandle`,
      16 `MethodType`, 17 `Dynamic`, 18 `InvokeDynamic`, 19 `Module`, 20 `Package`. `[NUM]`
      `[SOURCE]` `[RESEARCH]`
1.2.9 `CONSTANT_Long` and `CONSTANT_Double` occupy **two** constant pool slots; the second is
      unusable. JVMS calls this "a poor choice". `[TRAP]` `[SOURCE]` `[NUM]`
1.2.10 Modified UTF-8 in `CONSTANT_Utf8`: NUL encoded as two bytes `0xC0 0x80`, supplementary
       characters encoded as a surrogate pair of three-byte sequences. Not standard UTF-8, and the
       reason a naive parser mangles emoji in string constants. `[TRAP]` `[NUM]` `[RESEARCH]`
1.2.11 The 64 KB limits that fall out of `u2` fields: 65535 constant pool entries, 65535 bytes of
       bytecode per method (`code_length` is `u4` but the verifier and `LineNumberTable` cap it at
       65535), 65535 methods, 65535 fields, 255 method parameters (`long`/`double` count as two).
       These are the actual "method too large" and "too many constants" compile errors. `[NUM]`
       `[TRAP]`
1.2.12 `access_flags` for the class: `ACC_PUBLIC 0x0001`, `ACC_FINAL 0x0010`, `ACC_SUPER 0x0020`,
       `ACC_INTERFACE 0x0200`, `ACC_ABSTRACT 0x0400`, `ACC_SYNTHETIC 0x1000`,
       `ACC_ANNOTATION 0x2000`, `ACC_ENUM 0x4000`, `ACC_MODULE 0x8000`. `[NUM]` `[SOURCE]`
1.2.13 `ACC_SUPER` as a fossil: it changed `invokespecial` semantics for superclass methods, is set
       by every modern compiler, and is *ignored* from class file version 52 onward. `[RESEARCH]`
       `[VERSION-TRAP]`
1.2.14 `this_class`, `super_class` (0 only for `java/lang/Object`), `interfaces[]`.
1.2.15 `field_info` and `method_info`: access flags, name index, descriptor index, attributes.
1.2.16 Field and method **descriptors**, the grammar in full: `B` byte, `C` char, `D` double,
       `F` float, `I` int, `J` long, `S` short, `Z` boolean, `V` void, `[` array,
       `Lfully/qualified/Name;` reference. `(Ljava/lang/String;I)V` read aloud. `[NUM]` `[SOURCE]`
1.2.17 Why the return type is part of the *descriptor* but not part of Java overload resolution —
       and how bridge methods and covariant returns exploit that. `[X-REF 03]` `[PROVE]`
1.2.18 The attribute mechanism: attributes are name-indexed, length-prefixed, and **unknown
       attributes must be silently ignored**, which is what makes the format extensible.
       `[SOURCE]`
1.2.19 The attribute inventory that matters: `Code`, `StackMapTable`, `Exceptions`,
       `LineNumberTable`, `LocalVariableTable`, `LocalVariableTypeTable`, `SourceFile`, `Signature`,
       `ConstantValue`, `Deprecated`, `Synthetic`, `RuntimeVisibleAnnotations`,
       `RuntimeInvisibleAnnotations`, `RuntimeVisibleTypeAnnotations`, `AnnotationDefault`,
       `BootstrapMethods`, `InnerClasses`, `EnclosingMethod`, `MethodParameters`, `Module`,
       `ModulePackages`, `ModuleMainClass`, `NestHost`, `NestMembers`, `Record`,
       `PermittedSubclasses`. `[RESEARCH]` `[SOURCE]`
1.2.20 The `Code` attribute's own structure: `max_stack`, `max_locals`, `code[]`,
       `exception_table[]`, and nested attributes. `max_stack`/`max_locals` are computed by the
       compiler and *checked* by the verifier. `[NUM]`
1.2.21 The exception table as four-tuples `(start_pc, end_pc, handler_pc, catch_type)`, with
       `catch_type = 0` meaning "any" — which is how `finally` and synchronized-block release are
       compiled. `[SOURCE]` `[BYTECODE]`
1.2.22 `RuntimeVisibleAnnotations` vs `RuntimeInvisibleAnnotations` is exactly
       `@Retention(RUNTIME)` vs `@Retention(CLASS)`; `SOURCE` retention emits nothing at all. This
       is why a Lombok annotation is invisible to reflection and a Spring one is not. `[X-REF 03]`
       `[X-REF 07]` `[PROVE]`
1.2.23 `Signature` carries the *generic* type that erasure removed, which is how
       `ParameterizedType` reflection works at all despite erasure. `[X-REF 03]` `[TRAP]`
1.2.24 `NestHost`/`NestMembers` (Java 11, JEP 181) replaced the synthetic `access$000` bridge
       methods that used to give outer/inner classes access to each other's privates.
       `[RESEARCH]` `[VERSION-TRAP]`
1.2.25 `Record` and `PermittedSubclasses` as the class-file face of records and sealed types.
       `[X-REF 04]`
1.2.26 `LineNumberTable` and `LocalVariableTable` are optional debug info controlled by
       `javac -g`; strip them and stack traces lose line numbers and debuggers lose parameter
       names. `-parameters` is a separate flag that emits `MethodParameters`. `[FLAG]` `[TRAP]`
1.2.27 The `java.lang.classfile` API (JEP 484, final in Java 24) as the JDK's own supported parser
       and builder, replacing the internal ASM fork. `[RESEARCH]` `[VERSION-TRAP]`
1.2.28 Reading a class file by hand: `javap -v -p ClassName` and what each block of its output maps
       to in the structure above. `[BYTECODE]` `[DUMP]`

*(28 leaves)*

## §1.3 Bytecode and the execution model

1.3.1 The frame: an operand stack, a local variable array, and a reference to the run-time constant
      pool of the current class. Created on invocation, destroyed on return. `[SOURCE]`
1.3.2 Local variable slot 0 of an instance method is `this`; parameters follow; `long` and `double`
      each occupy **two** slots. `[NUM]` `[TRAP]`
1.3.3 Operand stack depth is statically known at every instruction — that property is what makes
      verification decidable. `[PROVE]`
1.3.4 The opcode space: 256 possible, ~205 in use, plus three reserved (`impdep1 0xFE`,
      `impdep2 0xFF`, `breakpoint 0xCA`). `[NUM]` `[RESEARCH]`
1.3.5 The instruction families, each named with representative opcodes: constants (`iconst_*`,
      `bipush`, `sipush`, `ldc`), loads (`iload`, `aload_0`), stores (`istore`, `astore`), stack
      (`dup`, `dup_x1`, `pop2`, `swap`), arithmetic (`iadd`, `ldiv`, `irem`, `ishl`, `iinc`),
      conversions (`i2l`, `d2i`, `i2b`), comparisons (`lcmp`, `dcmpg`, `if_icmplt`, `ifnull`),
      control (`goto`, `tableswitch`, `lookupswitch`, `ireturn`, `athrow`), references (`new`,
      `newarray`, `getfield`, `putstatic`, `invokevirtual`, `checkcast`, `instanceof`,
      `monitorenter`), and extended (`wide`, `multianewarray`, `ifnonnull`, `goto_w`). `[SOURCE]`
1.3.6 The type-prefix convention (`i`, `l`, `f`, `d`, `a`, `b`, `c`, `s`) and the missing
      combinations: there is no `bload`, because `byte`/`short`/`char`/`boolean` are all computed as
      `int` on the operand stack. This is the bytecode-level reason `byte b = b + 1;` does not
      compile. `[PROVE]` `[TRAP]` `[X-REF 03]`
1.3.7 The five invocation instructions and exactly what each dispatches on: `invokestatic` (no
      receiver), `invokespecial` (constructors, `private`, `super` — non-virtual),
      `invokevirtual` (vtable dispatch on the receiver's class), `invokeinterface` (itable search),
      `invokedynamic` (bootstrap method installs a `CallSite`, then behaves like a direct call).
      `[SOURCE]` `[NUM]`
1.3.8 `invokedynamic` end to end: `BootstrapMethods` attribute → bootstrap method invoked once →
      returns a `CallSite` holding a `MethodHandle` → the call site is *linked* and thereafter
      cheap. This is the machinery behind lambdas (`LambdaMetafactory`), string concatenation
      (`StringConcatFactory`, Java 9+), records' `equals`/`hashCode`/`toString`
      (`ObjectMethods`), and pattern-matching switch (`SwitchBootstraps`). `[X-REF 04]`
      `[RESEARCH]` `[SOURCE]`
1.3.9 **Trap:** "a lambda is an anonymous class". At class-file level it is an `invokedynamic` and a
      private synthetic method; the implementing class is spun at *runtime* by
      `LambdaMetafactory`, which is why you see `Foo$$Lambda$14/0x00000008000c1440` in stack traces
      and why lambdas cost startup time rather than class-count. `[TRAP]` `[X-REF 04]` `[BYTECODE]`
1.3.10 `tableswitch` versus `lookupswitch`: dense case values compile to an O(1) jump table, sparse
       ones to a binary-searched key table. This is why `switch` on dense ints beats an if-chain and
       why a `String` switch compiles to `hashCode` + `lookupswitch` + `equals`. `[PROVE]`
       `[BYTECODE]`
1.3.11 `String` concatenation across versions: `StringBuilder` chains before Java 9,
       `invokedynamic` + `StringConcatFactory` from Java 9. The old "always use StringBuilder in a
       loop" advice is *still right in a loop* and *wrong for a single expression*.
       `[VERSION-TRAP]` `[TRAP]` `[BYTECODE]`
1.3.12 `new` is two instructions plus a call: `new` (allocate, fields zeroed), `dup`,
       `invokespecial <init>`. The object exists in an uninitialised-but-allocated state between
       them, which is exactly the window the verifier tracks with the `uninitialized(offset)` type.
       `[PROVE]` `[BYTECODE]`
1.3.13 Field access: `getfield`/`putfield` (instance, receiver on stack) versus
       `getstatic`/`putstatic` (class, triggers initialisation).
1.3.14 Array instructions: `newarray` (primitive, with the atype codes 4–11),
       `anewarray` (reference), `multianewarray` (dimensions byte), `arraylength`, `aaload`,
       `iastore`, and the `ArrayStoreException` covariance check performed by `aastore` at runtime.
       `[TRAP]` `[X-REF 03]` `[NUM]`
1.3.15 `checkcast` and `instanceof` as real runtime instructions with a real cost, and why the JIT
       usually folds them to a klass-pointer compare. `[X-REF 03]`
1.3.16 `athrow`, the exception table search, and why exceptions are cheap to *throw* and expensive
       to *construct* (`fillInStackTrace` walks frames). `[PROVE]` `[X-REF 03]`
1.3.17 `monitorenter`/`monitorexit` for a synchronized block versus the `ACC_SYNCHRONIZED` flag for
       a synchronized method — no bytecodes at all in the latter case. `[X-REF 05]` `[BYTECODE]`
1.3.18 `jsr`/`ret` and their removal: used for `finally` inlining before Java 6, made verification
       undecidable in general, and are illegal from class file version 51 (Java 7) onward. `finally`
       is now compiled by duplicating the block. `[RESEARCH]` `[VERSION-TRAP]` `[PROVE]`
1.3.19 The `wide` prefix for local variable indexes above 255. `[NUM]`
1.3.20 `iinc` as the only instruction that reads-modifies-writes a local without touching the
       operand stack — and how `i++` versus `++i` compile identically as a statement and
       differently as an expression. `[BYTECODE]` `[TRAP]`
1.3.21 Reading `javap -c` fluently as an interview skill: locate the constant pool refs, count stack
       depth, spot the synthetic bridge, spot the `invokedynamic`. `[BYTECODE]`
1.3.22 Why bytecode is *not* an optimisation target: `javac` does almost no optimisation (constant
       folding of compile-time constants and dead-`if(false)` elimination are about it) because
       everything real is the JIT's job. `[PROVE]` `[TRAP]`
1.3.23 Compile-time constants (`static final` primitives/`String` with constant initialisers) are
       **inlined into the calling class file** via `ConstantValue`, so changing one and recompiling
       only the defining class leaves stale values in callers. `[TRAP]` `[X-REF 03]` `[PROVE]`
1.3.24 Bytecode manipulation in the wild: ASM, ByteBuddy, Javassist, cglib — who uses each (Spring
       CGLIB proxies, Mockito, JaCoCo, APM agents) and what they cost in metaspace and startup.
       `[X-REF 07]` `[RESEARCH]`

*(24 leaves)*

## §1.4 Class loading — creation and loading (JVMS 5.3)

1.4.1 The three-phase model stated in the spec's own words: **loading** (find the bytes, derive a
      `Class`), **linking** (verification, preparation, resolution), **initialization** (run
      `<clinit>`). Everything people call "class loading" is these three. `[SOURCE]`
1.4.2 Loading is *lazy and on demand*: a class is loaded the first time it is needed, not when the
      JVM starts. The JVMS permits eager loading but requires errors to be reported only at the
      point of actual use. `[SOURCE]` `[PROVE]`
1.4.3 JVMS 5.3.1 loading by the bootstrap loader; 5.3.2 loading by a user-defined loader via
      `loadClass(N)`, which may either define the class itself or delegate to another loader.
      `[SOURCE]`
1.4.4 JVMS 5.3.3 array class creation: array classes are **created by the JVM, not loaded from
      bytes**; the defining loader of `Foo[]` is the defining loader of `Foo`, and of `int[]` is the
      bootstrap loader. `[SOURCE]` `[TRAP]`
1.4.5 JVMS 5.3.5 derivation, step by step: reject if this loader is already recorded as initiating
      for `N` (`LinkageError`), parse the `ClassFile` (`ClassFormatError`,
      `UnsupportedClassVersionError`, `NoClassDefFoundError` on name mismatch or `ACC_MODULE`),
      resolve the superclass (`ClassCircularityError`, `IncompatibleClassChangeError` if it is an
      interface or `final`, or if `PermittedSubclasses` is violated, or a `final` method is
      overridden), resolve superinterfaces. `[SOURCE]` `[RESEARCH]`
1.4.6 **Defining loader versus initiating loader**, the distinction almost nobody states correctly:
      the defining loader is the one that called `defineClass`; every loader in the delegation chain
      that was *asked* is an initiating loader. The JVM records all of them. `[SOURCE]` `[TRAP]`
      `[PROVE]`
1.4.7 **Class identity is the pair (binary name, defining loader).** Two loaders defining the same
      bytes produce two distinct, mutually incompatible runtime types. `[SOURCE]` `[PROVE]`
1.4.8 The consequence: `ClassCastException: com.acme.Order cannot be cast to com.acme.Order`, which
      looks impossible until you know 1.4.7. Diagnose with
      `obj.getClass().getClassLoader()` on both sides, or `jcmd VM.class_hierarchy`. `[TRAP]`
      `[DUMP]`
1.4.9 JVMS 5.3.4 **loading constraints**, written `N^L1 = N^L2`: the mechanism that stops two
      loaders from disagreeing about what a type name means across a method signature. Violation is
      a `LinkageError`. `[SOURCE]` `[RESEARCH]` `[PROVE]`
1.4.10 The **run-time package** = package name + defining loader. Package-private access and
       `protected` access are decided on run-time packages, not source packages — so the same
       package name loaded twice does *not* get package-private access. `[SOURCE]` `[TRAP]`
1.4.11 JVMS 5.3.6 modules and layers: run-time modules, `ModuleLayer`, the boot layer supplying
       `java.base` to the bootstrap loader, user-defined layers via `defineModules`, and the
       **unnamed module** that every classpath class lands in (reads every module, exports every
       package). `[SOURCE]` `[RESEARCH]`
1.4.12 JVMS 5.2 JVM startup: the initial class, `main`, and the bootstrap loader creating the
       initial thread. `[SOURCE]`
1.4.13 `ClassLoader`'s own API surface: `loadClass(String, boolean resolve)`, `findClass`,
       `defineClass`, `resolveClass`, `findLoadedClass`, `getResource`/`getResourceAsStream`,
       `getParent`, `getPlatformClassLoader`, `getSystemClassLoader`,
       `registerAsParallelCapable`. `[RESEARCH]`
1.4.14 The correct extension point is `findClass`, not `loadClass` — overriding `loadClass` is how
       you accidentally break delegation. `[TRAP]`
1.4.15 Parallel-capable class loaders (Java 7+): `registerAsParallelCapable()` switches the lock
       from the loader object to a per-class-name lock, removing a global bottleneck and a class of
       loader deadlocks. A loader that forgets it serialises all loading. `[RESEARCH]` `[TRAP]`
1.4.16 `Class.forName(String)` versus `Class.forName(name, initialize, loader)` versus
       `loader.loadClass(name)`: the first initialises and uses the *caller's* loader, the third
       does not initialise at all. This is why `Class.forName("com.mysql.jdbc.Driver")` used to
       register the driver and `loadClass` would not have. `[TRAP]` `[PROVE]`
1.4.17 `ClassNotFoundException` (checked, from an explicit lookup, "never found") versus
       `NoClassDefFoundError` (an `Error`, "present at compile time, absent or **failed to
       initialise** at runtime"). The nastiest case is the second: an `ExceptionInInitializerError`
       fired once, and every later use throws `NoClassDefFoundError` for a class sitting right there
       on the classpath. Always search the log backwards for the first
       `ExceptionInInitializerError`. `[TRAP]` `[PROVE]`
1.4.18 The rest of the `LinkageError` family, each with the change that causes it:
       `NoSuchMethodError`, `NoSuchFieldError`, `IncompatibleClassChangeError`,
       `AbstractMethodError`, `IllegalAccessError`, `ClassCircularityError`, `VerifyError`,
       `UnsupportedClassVersionError`, `UnsatisfiedLinkError`, `ExceptionInInitializerError`,
       `BootstrapMethodError`. Each one is a *binary incompatibility* symptom, i.e. someone
       recompiled half the world. `[SOURCE]` `[X-REF 03]`
1.4.19 `ServiceLoader` and `META-INF/services` as the JDK's own dynamic-loading mechanism, and its
       module-path counterpart `provides ... with ...`. `[RESEARCH]`
1.4.20 The context classloader (`Thread.currentThread().getContextClassLoader()`): why frameworks
       need it (a bootstrap-loaded JDK class cannot see application classes), how app servers set
       it per request, and why it is a classic leak vector when a pool thread keeps a stale one.
       `[TRAP]` `[X-REF 05]`

*(20 leaves)*

## §1.5 Linking — verification, preparation, resolution (JVMS 5.4)

1.5.1 Verification exists because the JVM must run bytecode from untrusted or simply
      wrongly-generated sources without corrupting its own invariants. It is what makes `sun.misc.
      Unsafe` special: everything *else* is checked. `[PROVE]`
1.5.2 The four verification passes, historically: file format integrity, semantic checks on the
      class structure, bytecode verification (the dataflow pass), and symbolic-reference
      verification during resolution. `[RESEARCH]`
1.5.3 The type-inference verifier (class file < 50) versus the **split verifier** using
      `StackMapTable` (class file ≥ 50, mandatory from 51). The compiler now emits the type state
      at every branch target so the verifier is a single linear pass instead of a fixpoint
      iteration. `[SOURCE]` `[PROVE]` `[NUM]`
1.5.4 `StackMapTable` frame kinds by name: `same_frame`, `same_locals_1_stack_item_frame`,
      `same_locals_1_stack_item_frame_extended`, `chop_frame`, `same_frame_extended`,
      `append_frame`, `full_frame`. Generating these wrong is the number-one cause of
      `VerifyError` from a bytecode-manipulation agent. `[RESEARCH]` `[TRAP]`
1.5.5 What the verifier actually proves: no operand stack overflow/underflow, no type confusion, no
      uninitialised object use, no jump outside the method, locals initialised before read, `return`
      matches the descriptor, and no access violation of `final`. `[SOURCE]`
1.5.6 `-Xverify:none` / `-noverify` are **deprecated since Java 13 and ignored since Java 18** —
      remove them from your start scripts. `[FLAG]` `[VERSION-TRAP]` `[TRAP]` `[RESEARCH]`
1.5.7 Bootstrap-loaded classes skip verification by default (`-XX:-BytecodeVerificationLocal`,
      `-XX:+BytecodeVerificationRemote`), which is a startup optimisation and a trust decision.
      `[FLAG]` `[RESEARCH]`
1.5.8 **Preparation** (JVMS 5.4.2): static fields are created and set to their **default** values
      (0 / 0.0 / false / null) — *not* their initialisers. Explicit initialisers run in `<clinit>`
      at initialisation time. This is the mechanism behind "why did my static field read as null?"
      `[SOURCE]` `[PROVE]` `[TRAP]`
1.5.9 The exception: a `static final` field with a `ConstantValue` attribute gets its value during
      preparation, before `<clinit>` runs. `[SOURCE]` `[NUM]`
1.5.10 Preparation also imposes loading constraints for every overriding method (JVMS 5.4.2's
       `Ti^L1 = Ti^L2` rule over the return type and each parameter). `[SOURCE]` `[RESEARCH]`
1.5.11 **Resolution** (JVMS 5.4.3): turning a symbolic reference in the constant pool into a direct
       reference. Lazy — performed the first time an instruction that needs it executes.
       `[SOURCE]`
1.5.12 The seventeen instructions that trigger resolution: `anewarray`, `checkcast`, `getfield`,
       `getstatic`, `instanceof`, `invokedynamic`, `invokeinterface`, `invokespecial`,
       `invokestatic`, `invokevirtual`, `ldc`, `ldc_w`, `ldc2_w`, `multianewarray`, `new`,
       `putfield`, `putstatic`. `[SOURCE]` `[NUM]` `[RESEARCH]`
1.5.13 Resolution is **idempotent and sticky**: once it succeeds it always returns the same entity;
       once it fails it always throws the same error, and bootstrap methods are never re-run.
       `[SOURCE]` `[PROVE]`
1.5.14 5.4.3.1 class and interface resolution, and the `IllegalAccessError` from access control.
1.5.15 5.4.3.2 field resolution: search `C`, then its **superinterfaces** (recursively,
       depth-first), then its superclass. Note the interface-before-superclass order. Failure is
       `NoSuchFieldError`. `[SOURCE]` `[TRAP]`
1.5.16 5.4.3.3 method resolution: `IncompatibleClassChangeError` if `C` is an interface; then class
       hierarchy search including **signature-polymorphic** methods (`MethodHandle.invoke`,
       `invokeExact`, and the `VarHandle` access modes); then maximally-specific superinterface
       methods. `[SOURCE]` `[RESEARCH]`
1.5.17 5.4.3.4 interface method resolution, including `Object`'s public instance methods being
       visible through any interface, and the *maximally-specific* rule that resolves default-method
       diamonds. `[SOURCE]` `[X-REF 03]`
1.5.18 5.4.3.5 method type and method handle resolution: the nine `REF_*` kinds — `REF_getField 1`,
       `REF_getStatic 2`, `REF_putField 3`, `REF_putStatic 4`, `REF_invokeVirtual 5`,
       `REF_invokeStatic 6`, `REF_invokeSpecial 7`, `REF_newInvokeSpecial 8`,
       `REF_invokeInterface 9` — with the bytecode behaviour each denotes. `[SOURCE]` `[NUM]`
       `[RESEARCH]`
1.5.19 5.4.3.6 dynamically-computed constant and call site resolution: the bootstrap method receives
       `(Lookup, name, type, staticArgs...)`, may be invoked concurrently with one winner installed,
       wraps non-`Error` failures in `BootstrapMethodError`, and detects circular dynamic constants
       with `StackOverflowError`. `[SOURCE]` `[RESEARCH]`
1.5.20 5.4.4 **access control** in full: public + same module; public + reads + exports; non-public +
       same run-time package; protected + subclass (+ the receiver-type rule for instance members);
       private + same **nest**. Failure is `IllegalAccessError`. `[SOURCE]`
1.5.21 The nestmate algorithm (`NestHost`/`NestMembers`), including every fallback that makes a
       class its own nest host. `[SOURCE]` `[RESEARCH]`
1.5.22 5.4.5 **method overriding** as the JVM defines it — name + descriptor, not `ACC_PRIVATE`, and
       the transitive package-private overriding rule that surprises people across packages.
       `[SOURCE]` `[PROVE]` `[X-REF 03]`
1.5.23 5.4.6 **method selection**: resolution picks a method statically, selection picks the one
       actually run given the receiver's runtime class. Resolution ≠ selection is the precise
       statement of "static binding vs dynamic dispatch". `[SOURCE]` `[PROVE]` `[TRAP]`
1.5.24 5.6 binding native method implementations, and `UnsatisfiedLinkError` as its failure.
       `[SOURCE]`
1.5.25 Binary compatibility (JLS 13) as the practical consequence of all of the above: which source
       changes are safe to ship without recompiling callers, and which produce
       `NoSuchMethodError` at 3 a.m. `[X-REF 03]` `[PROVE]`

*(25 leaves)*

## §1.6 Initialization and the class-initialization lock (JVMS 5.5)

1.6.1 `<clinit>` is a synthetic method the compiler builds from all static initialiser blocks and
      all static field initialisers, **in source order**. `[SOURCE]` `[BYTECODE]`
1.6.2 A class has no `<clinit>` at all if it has no static initialisers and no non-constant static
      field initialisers — which is what makes the holder idiom free. `[PROVE]` `[X-REF 05]`
1.6.3 The five triggers for initialisation, exhaustively: `new`/`getstatic`/`putstatic`/
      `invokestatic` on the class; first invocation of a `REF_getStatic`/`REF_putStatic`/
      `REF_invokeStatic`/`REF_newInvokeSpecial` method handle; certain reflective calls; a subclass
      being initialised (forces the superclass); and being the class that defines an assertion
      status. `[SOURCE]` `[NUM]`
1.6.4 What does **not** trigger initialisation: reading a compile-time constant (`static final int`
      with `ConstantValue`), declaring an array of the type, `loader.loadClass`,
      `Class.forName(n, false, l)`, and accessing a static field declared in a *superclass* through
      a subclass name. `[SOURCE]` `[TRAP]` `[PROVE]`
1.6.5 **Interfaces are not initialised by subclass initialisation** unless they declare default
      methods — a rule almost everyone gets wrong. `[SOURCE]` `[TRAP]` `[RESEARCH]`
1.6.6 The 12-step initialisation procedure in JVMS 5.5: synchronize on `LC`, then dispatch on the
      state — *being initialised by this thread* (return, recursion permitted), *being initialised
      by another thread* (block on `LC`), *initialised* (return), *erroneous*
      (`NoClassDefFoundError`), otherwise mark in-progress, release `LC`, initialise the superclass,
      run `<clinit>`, mark initialised and notify, or on exception mark erroneous and throw
      `ExceptionInInitializerError`. `[SOURCE]` `[PROVE]`
1.6.7 The four states of a `Class` object: not-yet-verified/prepared, being-initialised,
      fully-initialised, **erroneous**. The erroneous state is permanent. `[SOURCE]` `[NUM]`
1.6.8 `LC` is a **per-class lock owned by the JVM**, not the `Class` object's monitor. Locking on
      `MyClass.class` in user code does *not* interact with it. `[SOURCE]` `[TRAP]` `[X-REF 05]`
1.6.9 The guarantee this buys: `<clinit>` runs **exactly once**, thread-safely, with no user
      synchronization — the whole basis of the holder idiom and enum singletons. `[PROVE]`
      `[X-REF 05]`
1.6.10 **Class-initialisation deadlock**: two classes whose static initialisers reference each other
       from two threads deadlock on `LC(A)` and `LC(B)`. It is invisible to `jstack`'s deadlock
       detector because the locks are not Java monitors; you see two threads in
       `Class.forName0`/`<clinit>` and nothing else. `[TRAP]` `[DUMP]` `[X-REF 05]` `[RESEARCH]`
1.6.11 Circular static initialisation *within* one thread does **not** deadlock — it reads
       half-initialised state, giving default values silently. Show the classic A/B pair that prints
       `0`. `[PROVE]` `[TRAP]`
1.6.12 `ExceptionInInitializerError` wraps only the *first* failure, and thereafter every access
       throws `NoClassDefFoundError` with no cause attached. The original stack trace is in the log
       once and never again. `[TRAP]` `[PROVE]`
1.6.13 Static initialiser order versus instance initialiser order versus constructor order, all six
       steps, including the superclass-constructor-calls-overridden-method hazard. `[X-REF 03]`
       `[PROVE]`
1.6.14 `<init>` versus `<clinit>`: instance initialisation is a normal method invoked by
       `invokespecial`; class initialisation is invoked only by the JVM. `[SOURCE]`
1.6.15 Cost: a class with a heavy `<clinit>` (regex compilation, config parsing, a static map of
       10 000 entries) makes the *first* request that touches it slow, forever, in every JVM you
       start. This is a real startup-latency lever. `[NUM]` `[PROVE]`
1.6.16 Observing it: `-verbose:class`, `-Xlog:class+load=info`, `-Xlog:class+init=info`,
       `jcmd VM.classloader_stats`, and `jcmd VM.class_hierarchy`. `[FLAG]` `[DUMP]`

*(16 leaves)*

## §1.7 The classloader hierarchy in practice

1.7.1 The three built-in loaders in Java 9+: **bootstrap** (written in C++, `null` from
      `getClassLoader()`, loads `java.base` and friends), **platform** (formerly extension; loads
      the rest of the JDK modules), **application/system** (classpath and module path). `[NUM]`
      `[VERSION-TRAP]`
1.7.2 What changed in Java 9: `sun.misc.Launcher$AppClassLoader` → `jdk.internal.loader.
      ClassLoaders$AppClassLoader`, the extension loader became the platform loader,
      `rt.jar`/`tools.jar` are gone, and casting the system loader to `URLClassLoader` **throws**
      — the single most common Java 8 → 9+ migration break. `[TRAP]` `[VERSION-TRAP]` `[RESEARCH]`
1.7.3 **Parent-first delegation**: ask the parent, only load it yourself if the parent cannot. Why:
      security (you cannot replace `java.lang.String`) and consistency (one `java.lang.Object`).
      `[PROVE]`
1.7.4 The delegation walk written as the actual `loadClass` body: `findLoadedClass` → `parent.
      loadClass` (or bootstrap) → `findClass` → `resolveClass`. `[SOURCE]`
1.7.5 **Parent-last / child-first** loaders and where they are legitimate: web app servers isolating
      a WAR's dependency versions, OSGi, plugin systems. The cost is that you can now have two
      incompatible `com.acme.Order` types. `[TRAP]`
1.7.6 Why `java.*` cannot be defined by a user loader at all: `defineClass` throws
      `SecurityException` for the `java.` prefix regardless of delegation. `[SOURCE]` `[RESEARCH]`
1.7.7 The classpath: order matters, first match wins, duplicate classes across jars are silently
      shadowed. This is "jar hell", and the diagnosis is `-Xlog:class+load=info` to see which jar
      each class came from. `[TRAP]` `[DUMP]`
1.7.8 The module path and the layer model: named modules, automatic modules, the unnamed module,
      and `--add-opens`/`--add-exports`/`--add-modules` as the escape hatches. `[X-REF 03]`
      `[RESEARCH]`
1.7.9 Strong encapsulation timeline: illegal reflective access warned in 9, denied by default in 16
      (JEP 396), `--illegal-access` removed in 17 (JEP 403), JNI restricted in 24 (JEP 472), and
      `sun.misc.Unsafe` memory access deprecated for removal (JEP 471/498). `[VERSION-TRAP]`
      `[RESEARCH]`
1.7.10 Custom loader use cases: app servers, OSGi, plugin architectures, hot reload, per-tenant
       isolation, and defining classes from generated bytes.
1.7.11 `MethodHandles.Lookup.defineHiddenClass` (Java 15, JEP 371) as the modern way to spin a class
       that is not discoverable by name and can be unloaded independently — the mechanism behind
       lambdas and `LambdaMetafactory` today. Anonymous classes via `Unsafe.defineAnonymousClass`
       were removed in Java 17. `[RESEARCH]` `[VERSION-TRAP]`
1.7.12 **Class unloading**: a class can only be collected when its defining loader, all its
       instances, and its `Class` object are unreachable — i.e. loaders are unloaded as a unit.
       `[PROVE]` `[SOURCE]`
1.7.13 The **classloader leak**, in full: any strong reference from a longer-lived context pins the
       loader and every class it defined, leaking metaspace on each redeploy. The five classic
       roots: a static field in a JDK/bootstrap class, a `ThreadLocal` on a pooled thread, a JDBC
       driver still registered in `DriverManager`, a running timer/pool thread created by the app,
       and a JVM shutdown hook or MBean still registered. `[TRAP]` `[X-REF 05]`
1.7.14 Two more that catch people: a `java.util.logging` `Level` cached in a static map, and a
       custom `URL` stream handler / `SecurityProvider` registered globally. `[RESEARCH]`
1.7.15 Diagnosing a loader leak: heap-dump the JVM, find instances of your `WebappClassLoader`,
       count them (>1 after redeploy = leak), and run **path to GC roots** on the extra ones.
       `jcmd VM.classloaders` and `VM.classloader_stats` give the live picture without a dump.
       `[DUMP]` `[PROVE]`
1.7.16 `-Xlog:class+unload=info` to prove unloading is or is not happening, and
       `-XX:+ClassUnloadingWithConcurrentMark` (G1) as the knob that governs when it can.
       `[FLAG]` `[RESEARCH]`
1.7.17 Hot reload mechanisms compared: HotSwap via JVMTI (method bodies only), DCEVM/JetBrains
       enhanced HotSwap, Spring Boot DevTools' two-loader restart trick, JRebel. Say precisely what
       each can and cannot change. `[X-REF 07]` `[RESEARCH]`
1.7.18 Spring Boot's fat-jar loader (`org.springframework.boot.loader.launch.JarLauncher` and the
       nested-jar `LaunchedClassLoader`), and why `BOOT-INF/classes` and `BOOT-INF/lib` exist rather
       than a shaded uber-jar. `[X-REF 07]` `[RESEARCH]`
1.7.19 `-verbose:class` versus `-Xlog:class+load=info:file=classes.log` — the modern spelling, and
       the count of loaded classes as a startup metric. `[FLAG]` `[NUM]`
1.7.20 Class-loading cost at scale: a Spring Boot service loads 8 000–20 000 classes at startup;
       each costs a file read, a parse, verification and possibly a `<clinit>`. That is what CDS and
       the AOT cache attack. `[NUM]` `[RESEARCH]`

*(20 leaves)*

## §1.8 Runtime data areas (JVMS 2.5)

1.8.1 The full area inventory with lifetime, sharing and failure mode, as one table: **heap**
      (shared, all objects/arrays, `OutOfMemoryError: Java heap space`), **method area / metaspace**
      (shared, class metadata, `OutOfMemoryError: Metaspace`), **run-time constant pool** (per class,
      inside metaspace), **JVM stacks** (per thread, frames, `StackOverflowError` or
      `OutOfMemoryError` on creation), **PC register** (per thread, no error), **native method
      stacks** (per thread), plus the HotSpot-specific **code cache** and **direct/native memory**.
      `[SOURCE]`
1.8.2 Which of these the JVMS mandates and which are HotSpot implementation choices: metaspace, the
      code cache and TLABs are not in the spec; the heap, stacks, PC and method area are.
      `[TRAP]` `[SOURCE]`
1.8.3 The stack frame in detail: local variable array, operand stack, run-time constant pool
      reference, and (implementation-specific) return address and previous-frame link. `[SOURCE]`
1.8.4 `-Xss` (a.k.a. `-XX:ThreadStackSize`): default ~1 MB on 64-bit Linux, 512 KB on some
      platforms; reserved virtual, committed lazily page by page, plus a guard page. `[FLAG]`
      `[NUM]` `[RESEARCH]`
1.8.5 `StackOverflowError` is an `Error`, not an `Exception`; catching it is legal but the stack
      state is untrustworthy and any `finally` may itself overflow. Typical depth at 1 MB is
      ~10 000–20 000 frames for simple methods — quote it as an order of magnitude, not a constant,
      because frame size varies with locals. `[NUM]` `[TRAP]`
1.8.6 The three real-world causes of `StackOverflowError`: unbounded recursion, mutual recursion
      through a framework (a Jackson serialiser on a cyclic object graph), and very deep
      proxy/filter chains. Read the *repeating cycle* in the trace, not the top frame. `[DUMP]`
      `[TRAP]`
1.8.7 `-XX:MaxJavaStackTraceDepth` (default 1024) truncating the trace you need. `[FLAG]` `[NUM]`
      `[RESEARCH]`
1.8.8 Thread stacks are **native** memory, not heap. 2 000 threads × 1 MB = 2 GB of reserved address
      space that `-Xmx` does not account for. This is a top-three cause of container OOMKills.
      `[NUM]` `[PROVE]` `[X-REF 19]`
1.8.9 `OutOfMemoryError: unable to create new native thread` versus the same failure expressed as
      `pthread_create failed (EAGAIN)` in `hs_err`: the limit is `ulimit -u`, `threads-max`,
      `pid_max`, or container `pids.max`, not the heap. `[TRAP]` `[X-REF 11]`
1.8.10 The heap layout HotSpot actually uses: a contiguous reserved address range, committed
       incrementally between `-Xms` and `-Xmx`, subdivided by the collector (generations for
       Serial/Parallel, regions for G1/ZGC/Shenandoah). `[NUM]`
1.8.11 `-Xms`/`-XX:InitialHeapSize` and `-Xmx`/`-XX:MaxHeapSize`; setting them equal removes resize
       pauses and heap-uncommit churn and makes behaviour predictable. `[FLAG]` `[PROVE]`
1.8.12 The default heap sizing ergonomics with no flags at all: `-XX:InitialRAMPercentage` 1.5625%,
       `-XX:MinRAMPercentage` 50% (for small machines), `-XX:MaxRAMPercentage` **25%**. Verify with
       `java -XX:+PrintFlagsFinal -version | grep -i ramper`. `[FLAG]` `[NUM]` `[RESEARCH]`
1.8.13 `-XX:+AlwaysPreTouch`: touches every heap page at startup so the first requests do not pay
       page-fault cost, at the price of a slower start and a full RSS from second zero. `[FLAG]`
       `[PROVE]`
1.8.14 Large pages: `-XX:+UseLargePages`, `-XX:+UseTransparentHugePages`, and the TLB-miss argument
       for why they help large heaps. `[FLAG]` `[RESEARCH]`
1.8.15 The **run-time constant pool** as the per-class runtime form of the class file's constant
       pool, living in metaspace, and holding the resolved direct references from §1.5.
       `[SOURCE]`
1.8.16 The string table (interned strings) as a separate native hash table:
       `-XX:StringTableSize` (default 65536, must be prime-ish for distribution),
       `jcmd VM.stringtable`, and the fact that the *strings themselves* live on the heap since
       Java 7. `[FLAG]` `[NUM]` `[X-REF 03]` `[RESEARCH]`
1.8.17 The symbol table for class/method/field names, `jcmd VM.symboltable`, and why a code base
       generating millions of distinct class names grows it without bound. `[RESEARCH]`
1.8.18 Per-thread native structures the JVM keeps beside the Java stack: the `JavaThread`, the
       handle area, the `Thread` object on the heap, and the OS `task_struct`. Roughly 1 KB of Java
       heap for megabytes of native stack. `[NUM]` `[X-REF 05]`
1.8.19 A single worked **total-footprint equation** for a container:
       `RSS ≈ heap_committed + metaspace + compressed_class_space + code_cache + (threads × Xss)
       + direct_buffers + GC_structures + JVM_internals + malloc_arenas + mapped_libraries`,
       with a real 2 GB-limit example filled in and summed. `[NUM]` `[PROVE]`
1.8.20 **Trap:** "the heap is the JVM's memory." Setting `-Xmx` to the container limit guarantees an
       eventual OOMKill, because every term above is outside `-Xmx`. `[TRAP]`

*(20 leaves)*

## §1.9 The heap, object allocation and the generational model

1.9.1 Where objects go: **all** objects and arrays are heap-allocated per the JVMS; "stack
      allocation" in Java is an *emergent* effect of escape analysis, not a language feature.
      `[TRAP]` `[PROVE]`
1.9.2 The allocation fast path is a **pointer bump** in a thread-local buffer — typically ~10
      machine instructions, on the order of a nanosecond. This is why Java allocation is genuinely
      cheaper than `malloc`. `[NUM]` `[PROVE]` `[ASM]`
1.9.3 TLAB (Thread-Local Allocation Buffer): each thread owns a slice of Eden and bumps a pointer in
      it with no synchronization at all. `[NUM]`
1.9.4 The three allocation paths in order: TLAB pointer bump → TLAB refill (a shared-heap CAS) →
      slow path / direct old-gen allocation for humongous objects. `[PROVE]`
1.9.5 Zeroing: newly allocated memory must be zeroed for JVMS field-default semantics; HotSpot
      pre-zeroes TLAB chunks and the JIT elides redundant zeroing where it can prove immediate
      overwrite. `[SOURCE]` `[RESEARCH]`
1.9.6 The **generational hypothesis**: most objects die young; few references point from old
      objects to young ones. Both halves are needed — the second is what makes remembered sets
      small. `[PROVE]`
1.9.7 Young generation layout: Eden + two survivor spaces `S0`/`S1`, with exactly one survivor
      always empty because young collection is a **copying** collector. `[NUM]`
1.9.8 Why copying collection costs live data, not garbage: the collector traces and copies survivors
      and then declares the whole region free. Doubling the garbage costs nothing. This is the
      single most important cost fact in Java performance. `[PROVE]` `[NUM]`
1.9.9 Tenuring: `-XX:MaxTenuringThreshold` (default 15, the age field is 4 bits in the mark word),
      `-XX:InitialTenuringThreshold`, `-XX:TargetSurvivorRatio` (default 50), and adaptive tenuring
      that lowers the threshold when survivor space is tight. `[FLAG]` `[NUM]` `[RESEARCH]`
1.9.10 **Premature promotion**: survivor space too small → objects promoted early → old gen fills →
       full GCs. Diagnose with `-Xlog:gc+age=trace` and the age histogram. `[TRAP]` `[DUMP]`
1.9.11 Sizing knobs: `-XX:NewRatio` (default 2, i.e. young = 1/3 of heap),
       `-XX:SurvivorRatio` (default 8, i.e. each survivor = 1/10 of young), `-Xmn`/`-XX:NewSize`/
       `-XX:MaxNewSize`, and the fact that G1 ignores most of them in favour of
       `G1NewSizePercent`/`G1MaxNewSizePercent`. `[FLAG]` `[NUM]` `[TRAP]`
1.9.12 Old generation and the promotion path; "major GC" versus "full GC" versus "mixed GC" are
       three different events and the terms are used interchangeably by people who should not.
       `[TRAP]`
1.9.13 Allocation rate as the primary GC metric: MB/s allocated, measurable from GC logs
       (Eden size × young-GC frequency) or `jdk.ObjectAllocationSample` in JFR. Tuning the collector
       before measuring the allocation rate is the classic wasted week. `[NUM]` `[PROVE]`
       `[RESEARCH]`
1.9.14 Live-set size as the second metric: old-gen occupancy *after* a full GC. This is the number
       that determines the heap you actually need. `[NUM]` `[PROVE]`
1.9.15 Object graph reachability and **GC roots**, enumerated exactly: local variables and operands
       in every frame of every thread, static fields of loaded classes, JNI local and global
       references, active monitors, the system class loader and interned strings, `Class` objects of
       loaded classes, and JVM-internal roots. `[SOURCE]` `[PROVE]`
1.9.16 Reachability is transitive; "unreferenced" is not the criterion. Two objects referencing only
       each other are unreachable and collectable — reference counting would leak them, tracing does
       not. `[PROVE]` `[TRAP]`
1.9.17 The five reachability levels: strongly, softly, weakly, phantom reachable, and unreachable.
       `[SOURCE]` (full treatment in §1.13)
1.9.18 Object alignment: `-XX:ObjectAlignmentInBytes` default 8, so every object size rounds up to a
       multiple of 8 and a 13-byte object occupies 16. Raising it to 16 buys a larger
       compressed-oops range at the cost of padding waste. `[FLAG]` `[NUM]` `[PROVE]`
1.9.19 Memory-footprint arithmetic worked end to end for `new Integer(1)`, `new int[10]`,
       `new String("hello")`, an `ArrayList` of 1000 `Long`s, and a `HashMap` entry — header +
       fields + padding + referenced objects, in bytes. `[NUM]` `[PROVE]` `[X-REF 02]`
1.9.20 JOL (`java.openjdk.jol`) as the tool that prints the actual layout:
       `ClassLayout.parseInstance(o).toPrintable()` and `GraphLayout.parseInstance(o).totalSize()`.
       `[RESEARCH]` `[DUMP]`

*(20 leaves)*

## §1.10 Object layout, headers, oops and klasses

1.10.1 The HotSpot vocabulary: an **oop** is an "ordinary object pointer"; `oopDesc` is the object's
       header struct; a **Klass** is the VM-internal metadata object describing a type; `Class` is
       the Java mirror of a `Klass`. `[SOURCE]` `[RESEARCH]`
1.10.2 The classic 64-bit header: **mark word 8 bytes** + **klass pointer 4 bytes** (compressed) or
       8 bytes (uncompressed) = 12 or 16 bytes, then fields, then padding to 8. Arrays add a 4-byte
       `length`, giving 16 bytes of header. `[NUM]` `[PROVE]` `[RESEARCH]`
1.10.3 The mark word's overloaded contents by lock state: unlocked (hash code 31 bits, age 4 bits,
       biased bit, tag `01`), stack-locked (pointer to the displaced header in the `BasicLock`, tag
       `00`), inflated (pointer to `ObjectMonitor`, tag `10`), marked-for-GC (forwarding pointer,
       tag `11`). `[NUM]` `[SOURCE]` `[X-REF 05]`
1.10.4 The identity hash code lives **in the mark word**, is computed lazily on first
       `System.identityHashCode`, and is therefore *displaced* while the object is locked — which is
       why taking an identity hash disables biased locking historically and costs a word today.
       `[PROVE]` `[TRAP]` `[RESEARCH]`
1.10.5 The GC age field is 4 bits, which is precisely why `MaxTenuringThreshold` cannot exceed 15.
       `[NUM]` `[PROVE]`
1.10.6 **Compact object headers**: JEP 450 experimental in Java 24, JEP 519 product in Java 25,
       JEP 534 proposes default. `-XX:+UseCompactObjectHeaders` folds the always-compressed klass
       pointer into the mark word, giving an **8-byte header**, and reported 10–20% live-set memory
       reduction on small-object-heavy workloads. `[FLAG]` `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
1.10.7 **Compressed oops** (`-XX:+UseCompressedOops`, on by default below 32 GB): store 32-bit
       offsets instead of 64-bit addresses, decode as `base + (narrow << 3)` using the 8-byte
       alignment shift. `[FLAG]` `[NUM]` `[PROVE]`
1.10.8 The three heap-placement strategies HotSpot tries: heap below 4 GB → no base, no shift;
       heap below 32 GB → zero-based, shift only; otherwise → base + shift. `[NUM]` `[SOURCE]`
       `[RESEARCH]`
1.10.9 **The 32 GB cliff:** raising `-Xmx` from 31 GB to 33 GB *reduces* usable memory because every
       reference doubles in size. Either stay under the threshold or jump well past it. `[TRAP]`
       `[NUM]` `[PROVE]`
1.10.10 `-XX:+UseCompressedClassPointers` and the **compressed class space**
        (`-XX:CompressedClassSpaceSize`, default 1 GB reserved) as a distinct reservation inside
        metaspace. `[FLAG]` `[NUM]` `[RESEARCH]`
1.10.11 Field layout rules: HotSpot reorders fields by size (longs/doubles, then ints/floats, then
        shorts/chars, then bytes/booleans, then references) to minimise padding, and
        `-XX:+CompactFields`/`-XX:FieldsAllocationStyle` control the details. Declaration order is
        **not** memory order. `[TRAP]` `[NUM]` `[RESEARCH]`
1.10.12 Superclass fields precede subclass fields, and inheritance-induced padding is why a deep
        hierarchy of tiny classes wastes memory. `[NUM]` `[PROVE]`
1.10.13 `@Contended` (`jdk.internal.vm.annotation.Contended`, requires
        `-XX:-RestrictContended` outside the JDK) pads a field to its own cache line;
        `-XX:ContendedPaddingWidth` default 128 bytes. `[FLAG]` `[NUM]` `[X-REF 05]`
1.10.14 The `Klass` hierarchy: `Klass` → `InstanceKlass` (with `InstanceMirrorKlass`,
        `InstanceClassLoaderKlass`, `InstanceRefKlass` subclasses) and `ArrayKlass` →
        `ObjArrayKlass`/`TypeArrayKlass`. `[SOURCE]` `[RESEARCH]`
1.10.15 What an `InstanceKlass` holds: the constant pool, the method array, the field descriptors,
        the **vtable** and **itable**, the mirror `Class` object, the `ClassLoaderData` link, the
        superclass and interface pointers, and the initialisation state. `[SOURCE]`
1.10.16 **vtable** dispatch for `invokevirtual`: one indirection through the klass, constant time.
        **itable** dispatch for `invokeinterface`: find the interface's itable entry first, hence
        historically slower — and the reason `invokeinterface` used to be the "expensive" call.
        `[PROVE]` `[NUM]` `[RESEARCH]`
1.10.17 `ClassLoaderData` and `ClassLoaderDataGraph` as the unit of metaspace ownership and class
        unloading — the implementation of "loaders are unloaded as a unit". `[SOURCE]`
1.10.18 Where the `Class` object lives: on the **heap** since Java 8 (it was in PermGen before), with
        its metadata in metaspace. Static fields live in the mirror `Class` object on the heap.
        `[VERSION-TRAP]` `[TRAP]` `[NUM]` `[RESEARCH]`
1.10.19 Array layout: header (mark + klass + length) + elements + padding; element size 1/2/4/8 by
        type, with `boolean[]` costing one byte per element and `long[]` eight. Worked byte counts
        for `new boolean[10]`, `new long[10]`, `new String[10]`. `[NUM]` `[PROVE]`
1.10.20 The maximum array length: `Integer.MAX_VALUE - 8` in practice (the header steals a few
        slots), giving `OutOfMemoryError: Requested array size exceeds VM limit`, which is a
        different error from `Java heap space`. `[NUM]` `[TRAP]`
1.10.21 The per-object overhead argument for primitives-over-boxes and arrays-over-collections, with
        the arithmetic: a `Long` is 16 bytes plus an 8-byte reference versus 8 bytes for a `long`
        array slot — 3× for the same data. `[NUM]` `[PROVE]` `[X-REF 02]`
1.10.22 Project Valhalla's value classes as the eventual fix, and why it is the largest outstanding
        change to this section. `[RESEARCH]` `[X-REF 03]`
1.10.23 Reading a real JOL dump line by line: offsets, sizes, the `(object header: mark)` and
        `(object header: class)` rows, `(alignment/padding gap)` and `Instance size`. `[DUMP]`
        `[NUM]`

*(23 leaves)*

## §1.11 Garbage collection — the model and the vocabulary

1.11.1 Why automatic memory management at all: manual `free` produces use-after-free, double-free
       and leaks, and those are the top memory-safety CVE classes. GC trades throughput and
       predictability for the elimination of an entire bug family. `[PROVE]`
1.11.2 **GC tracks live objects, not garbage.** Nothing ever "visits" a dead object; the collector
       marks what is reachable and reclaims the complement wholesale. Every cost model in this
       section follows from that one sentence. `[TRAP]` `[PROVE]` `[RESEARCH]`
1.11.3 Tracing versus reference counting: cycles, write-barrier cost, and why no production JVM
       collector uses reference counting. `[PROVE]`
1.11.4 The four primitive algorithms and their costs: **mark-sweep** (fragmentation),
       **mark-compact** (slow but compacting), **copying/scavenge** (fast, needs 2× space),
       **mark-sweep-compact** (Serial's old-gen). `[NUM]`
1.11.5 Fragmentation and why it matters even with free memory available: a 2 MB allocation fails in
       a heap with 500 MB free in 4 KB holes. This is the failure CMS died of. `[PROVE]` `[TRAP]`
1.11.6 The GC design triangle: **throughput**, **pause time**, **footprint** — pick two. Every
       collector in §1.12 is a point on this triangle and should be introduced as such. `[PROVE]`
1.11.7 **Stop-the-world** defined precisely: all Java threads brought to a safepoint, no application
       progress. Every collector has STW phases; they differ only in how long and how often.
       `[TRAP]`
1.11.8 Concurrent versus parallel versus incremental — three orthogonal properties constantly
       conflated. Parallel = many GC threads; concurrent = GC runs alongside the application;
       incremental = the work is split across many small pauses. `[TRAP]` `[PROVE]`
1.11.9 The floating-garbage problem: anything that dies *during* a concurrent mark is not collected
       this cycle. Concurrent collectors trade space for pause time. `[PROVE]`
1.11.10 **Allocation-rate-driven** thinking: GC frequency = allocation rate ÷ Eden size; GC cost per
        cycle ∝ live data. Both levers, stated as a formula and worked with real numbers. `[NUM]`
        `[PROVE]`
1.11.11 The **tri-colour abstraction**: white (unvisited), grey (visited, children pending), black
        (done). Marking terminates when no grey remains. `[PROVE]`
1.11.12 The **lost-object problem** in concurrent marking: the mutator writes a white object's
        reference into a black object and deletes the grey path, so a live object is never marked.
        Two invariants can prevent it. `[PROVE]` `[TRAP]`
1.11.13 **SATB** (snapshot-at-the-beginning, G1/Shenandoah) versus **incremental update** (CMS)
        versus **load-barrier colouring** (ZGC) as the three answers. SATB over-approximates
        liveness — anything alive at cycle start survives the cycle. `[PROVE]` `[RESEARCH]`
1.11.14 **Write barriers** and **read/load barriers**: small code fragments the JIT injects around
        heap reference stores or loads. They are the price of concurrency and generational
        collection, and they show in your throughput number, not your pause number. `[PROVE]`
        `[ASM]`
1.11.15 The **card table**: a byte array with one card per 512 bytes of heap, dirtied by the write
        barrier, scanned at collection time to find old→young references without walking the whole
        old gen. `[NUM]` `[PROVE]` `[SOURCE]`
1.11.16 **Remembered sets** as the generalisation for region-based collectors: per-region records of
        "who points into me", so a region can be collected independently. `[SOURCE]`
1.11.17 The **collection set (CSet)**: the regions chosen for this collection, and how choosing it
        by garbage density is exactly what "Garbage First" means. `[PROVE]`
1.11.18 **Evacuation** and evacuation failure ("to-space exhausted"): the collector runs out of free
        regions to copy into mid-pause, and must fall back — the single most common cause of a
        surprise multi-second G1 pause. `[TRAP]` `[DUMP]` `[RESEARCH]`
1.11.19 **Compaction** and why it is what makes pointer-bump allocation possible at all: without
        compaction you need a free list, and allocation stops being ~1 ns. `[PROVE]`
1.11.20 Safepoints as GC's precondition: the collector needs precise **oop maps** at every
        stack frame, which only exist at safepoints. This is why GC pauses and safepoints are the
        same conversation. `[X-REF §1.17]` `[PROVE]`
1.11.21 GC threads: `-XX:ParallelGCThreads` (default ≈ `min(ncpu, 8) + (ncpu-8)*5/8` above 8 CPUs)
        and `-XX:ConcGCThreads` (default ≈ `ParallelGCThreads / 4`). Both derive from
        `availableProcessors()`, which is wrong in a fractional-CPU container. `[FLAG]` `[NUM]`
        `[TRAP]` `[RESEARCH]`
1.11.22 `System.gc()` is a **hint**: it may be ignored, it is disabled by `-XX:+DisableExplicitGC`,
        it is redirected to a concurrent cycle by `-XX:+ExplicitGCInvokesConcurrent`, and by default
        it triggers a full STW collection. Never call it in application code; do audit the
        libraries that do (NIO's `Bits.reserveMemory`, RMI DGC). `[FLAG]` `[TRAP]` `[RESEARCH]`
1.11.23 RMI distributed GC's `sun.rmi.dgc.server.gcInterval` (default 1 hour since Java 6) as the
        classic source of a mysterious hourly full GC. `[TRAP]` `[NUM]` `[RESEARCH]`
1.11.24 GC ergonomics: with no flags, the JVM picks a collector and sizes based on machine class.
        Since Java 9 the answer is G1 on any machine with ≥2 CPUs and ≥1792 MB of memory, and Serial
        below that — which is why your 1-CPU container silently uses Serial. `[NUM]` `[TRAP]`
        `[RESEARCH]`
1.11.25 The GC-pause budget as an SLO input: if p99 latency must be 200 ms and GC pauses are 150 ms
        at 3/minute, GC alone can blow the SLO. Do the arithmetic. `[NUM]` `[PROVE]` `[X-REF 20]`
1.11.26 GC overhead as a percentage of wall time, and the two thresholds worth remembering: >5%
        means investigate, >98% with <2% reclaimed is what triggers
        `GC overhead limit exceeded`. `[NUM]`

*(26 leaves)*

## §1.12 The collectors

1.12.1 The full inventory with flag, character, and when to choose it, as one table:
       Serial `-XX:+UseSerialGC`, Parallel `-XX:+UseParallelGC`, **G1 `-XX:+UseG1GC` (default since
       Java 9)**, ZGC `-XX:+UseZGC`, Shenandoah `-XX:+UseShenandoahGC`, Epsilon
       `-XX:+UseEpsilonGC` (+`-XX:+UnlockExperimentalVMOptions`). `[FLAG]` `[NUM]`
1.12.2 The dead ones and their removal releases: CMS deprecated in Java 9 (JEP 291) and **removed in
       Java 14** (JEP 363); the incremental/CMS combinations removed in Java 9 (JEP 214). Any guide
       still teaching CMS tuning is describing a JVM you cannot run. `[VERSION-TRAP]` `[TRAP]`
       `[RESEARCH]`
1.12.3 **Serial**: one thread, mark-copy young + mark-sweep-compact old, smallest footprint, no
       barrier overhead beyond the card table. Genuinely the right answer for a 1-CPU, small-heap
       container and for short-lived batch JVMs. The "Serial is toy" claim is folklore. `[TRAP]`
       `[RESEARCH]`
1.12.4 **Parallel** (a.k.a. throughput collector): multi-threaded STW young and old, best raw
       throughput per CPU, unbounded pauses at large heaps. Right for batch and analytics where
       pauses do not matter. `-XX:GCTimeRatio` (default 99, i.e. a 1% GC-time target) and
       `-XX:MaxGCPauseMillis` as its adaptive-sizing inputs; `-XX:+UseAdaptiveSizePolicy` on by
       default. `[FLAG]` `[NUM]` `[RESEARCH]`
1.12.5 **G1** overview: region-based, generational, incremental, evacuating, mostly-concurrent,
       pause-goal driven. The heap is split into 1 MB–32 MB power-of-two **regions**, targeting
       ~2048 of them; each region is dynamically Eden, Survivor, Old, Humongous or Free. `[NUM]`
       `[FLAG]` `[RESEARCH]`
1.12.6 G1's flag surface with defaults, every one worth knowing: `-XX:MaxGCPauseMillis` (200),
       `-XX:G1HeapRegionSize` (ergonomic), `-XX:InitiatingHeapOccupancyPercent` (45, adaptive by
       default via `-XX:+G1UseAdaptiveIHOP`), `-XX:G1NewSizePercent` (5),
       `-XX:G1MaxNewSizePercent` (60), `-XX:G1HeapWastePercent` (5),
       `-XX:G1MixedGCLiveThresholdPercent` (85), `-XX:G1MixedGCCountTarget` (8),
       `-XX:G1HeapReservePercent` (10), `-XX:G1PeriodicGCInterval`,
       `-XX:+G1EagerReclaimHumongousObjects` (on), `-XX:+UseStringDeduplication` (off). `[FLAG]`
       `[NUM]` `[RESEARCH]`
1.12.7 G1's cycle as a state machine: **young-only phase** (normal young collections → Concurrent
       Start → Remark → Cleanup → Prepare Mixed) then **space-reclamation phase** (a series of
       mixed collections), then back. Naming these correctly is an interview differentiator.
       `[SOURCE]` `[RESEARCH]`
1.12.8 The four sub-phases of every G1 pause as they appear in the log: Pre Evacuate Collection Set,
       **Merge Heap Roots**, Evacuate Collection Set, Post Evacuate Collection Set. `[DUMP]`
       `[RESEARCH]`
1.12.9 **Humongous objects**: anything ≥ half a region, allocated directly into contiguous Old
       regions, wasting the tail of the last region. A stream of large arrays therefore fills Old
       with no "old-gen leak" at all — the fix is usually a bigger `G1HeapRegionSize` or a smaller
       array. `[TRAP]` `[NUM]` `[PROVE]`
1.12.10 G1's remembered sets and their memory cost (historically up to ~10% of heap), and why
        `Merge Heap Roots` replaced the old separate "Update RS / Scan RS" phases. `[NUM]`
        `[RESEARCH]`
1.12.11 G1 full GC: single-threaded until Java 10, **parallel since Java 10** (JEP 307). A full GC
        in G1 is a *failure* signal, not a normal event. `[VERSION-TRAP]` `[TRAP]`
1.12.12 **ZGC**: region-based (ZPages: small 2 MB, medium 32 MB, large N×2 MB), fully concurrent
        marking, relocation and compaction, sub-millisecond pauses independent of heap size, scaling
        to 16 TB. `[NUM]` `[RESEARCH]`
1.12.13 ZGC's **coloured pointers**: metadata bits in the 64-bit pointer encoding marked/remapped/
        finalizable state, read by a **load barrier** that fixes up the pointer on the fly.
        Consequence: ZGC does not support compressed oops, so heaps below ~32 GB pay a
        reference-size penalty against G1. `[PROVE]` `[TRAP]` `[NUM]` `[RESEARCH]`
1.12.14 **Generational ZGC** (JEP 439, Java 21) adds young/old generations and a **store barrier**
        so marking work moves off the load path. Non-generational ZGC became non-default in Java 23
        (JEP 474) and was **removed in Java 24**. `-XX:+ZGenerational` is the Java 21 opt-in flag
        and is obsolete afterwards. `[FLAG]` `[VERSION-TRAP]` `[RESEARCH]`
1.12.15 ZGC's remaining pauses and what they are for: mark start, mark end, relocate start — each
        bounded by root-set size, not heap size. `[PROVE]` `[NUM]`
1.12.16 ZGC knobs: `-XX:SoftMaxHeapSize`, `-XX:ZCollectionInterval`, `-XX:ZAllocationSpikeTolerance`,
        `-XX:+ZUncommit` and `-XX:ZUncommitDelay` (default 300 s). ZGC deliberately has *few* knobs;
        the design position is "give it enough heap and CPU". `[FLAG]` `[NUM]` `[RESEARCH]`
1.12.17 ZGC's failure mode is **allocation stall**, not a long pause: if the mutator allocates faster
        than the collector can reclaim, threads block in `ZPageAllocator`. Look for
        `Allocation Stall` in `-Xlog:gc*`. `[TRAP]` `[DUMP]` `[RESEARCH]`
1.12.18 **Shenandoah**: region-based, concurrent evacuation using **Brooks forwarding pointers** and
        a **load reference barrier (LRB)**, supports compressed oops (unlike ZGC), and pause times
        independent of heap size. Generational mode is experimental in Java 24 (JEP 404) and a
        product feature in Java 25. `[NUM]` `[VERSION-TRAP]` `[RESEARCH]`
1.12.19 Shenandoah's modes: `-XX:ShenandoahGCMode=satb|iu|passive|generational`, and
        `-XX:ShenandoahGCHeuristics=adaptive|static|compact|aggressive`. `[FLAG]` `[RESEARCH]`
1.12.20 Shenandoah versus ZGC as a real decision: Shenandoah keeps compressed oops (better footprint
        under 32 GB) and ships in most OpenJDK builds but **not Oracle JDK**; ZGC scales further and
        has the simpler barrier. `[TRAP]` `[RESEARCH]`
1.12.21 **Epsilon** (`-XX:+UseEpsilonGC`, JEP 318): allocates and never collects; the JVM dies when
        the heap fills. Uses: measuring allocation footprint exactly, latency experiments with GC
        removed as a variable, and ultra-short-lived jobs. `[NUM]`
1.12.22 The **master collector comparison table** — pause behaviour, throughput cost, footprint cost,
        compressed-oops support, heap range, barrier type, generational, class unloading, and the
        one-line "choose it when". `[NUM]`
1.12.23 The decision procedure, stated as a rule rather than a preference: default to G1; move to
        ZGC when p99 pause is the binding constraint and you can pay ~10–15% throughput and extra
        heap; move to Parallel when only throughput matters; move to Serial for ≤1 CPU or small
        short-lived containers. Change nothing until you have GC logs. `[PROVE]`
1.12.24 **String deduplication** (`-XX:+UseStringDeduplication`, G1 since Java 8u20, all collectors
        since Java 18): the GC finds `String`s with equal `byte[]` contents and points them at one
        shared array. Distinct from `String.intern()`, which is a user-called native hash table.
        `[FLAG]` `[TRAP]` `[X-REF 03]` `[RESEARCH]`
1.12.25 Compact strings (JEP 254, Java 9): `String` holds a `byte[]` plus a `coder` byte instead of a
        `char[]`, halving Latin-1 string footprint. This is a layout change most memory guides still
        describe wrongly. `[VERSION-TRAP]` `[NUM]` `[X-REF 03]`
1.12.26 Heap uncommit: `-XX:+ShrinkHeapInSteps`, `-XX:MinHeapFreeRatio` (40) /
        `-XX:MaxHeapFreeRatio` (70), G1's periodic GC and ZGC's `ZUncommit`. Relevant when you are
        paying for memory you are not using. `[FLAG]` `[NUM]` `[RESEARCH]`
1.12.27 GC and `finalize`/`Cleaner`/`Reference` processing as a pause contributor —
        `-XX:+ParallelRefProcEnabled` and the `Reference Processing` line in the pause breakdown.
        `[FLAG]` `[DUMP]` `[RESEARCH]`

*(27 leaves)*

## §1.13 References, finalization and Cleaner

1.13.1 The four reference strengths in order and the exact collection rule for each: **strong**
       (never collected while reachable), **soft** (collected only under memory pressure, all soft
       refs guaranteed cleared before `OutOfMemoryError`), **weak** (collected at the next GC that
       finds the object weakly reachable), **phantom** (enqueued *after* finalisation, `get()`
       always returns null). `[SOURCE]` `[NUM]`
1.13.2 `-XX:SoftRefLRUPolicyMSPerMB` (default 1000): a soft reference survives roughly
       `free_heap_MB × 1000 ms` past its last access. This is the number behind "my soft-reference
       cache never evicts" and "my soft-reference cache evicts everything". `[FLAG]` `[NUM]`
       `[TRAP]` `[RESEARCH]`
1.13.3 **Trap:** using `SoftReference` as a cache. You get an unpredictable, GC-pressure-coupled
       eviction policy, extra reference-processing pause time, and no size bound. Use Caffeine with
       `maximumSize` + `expireAfterWrite`. `[TRAP]` `[X-REF 15]`
1.13.4 `ReferenceQueue<T>` and the enqueue protocol; `Reference.get`, `clear`, `enqueue`,
       `isEnqueued` (deprecated), `refersTo` (Java 16+, the correct way to test identity without
       resurrecting a soft/weak referent). `[RESEARCH]`
1.13.5 `Reference.reachabilityFence(Object)` (Java 9): the fix for an object being collected while a
       native resource derived from it is still in use — the JIT can prove `this` dead before your
       method returns. `[TRAP]` `[PROVE]` `[RESEARCH]`
1.13.6 `WeakHashMap`: weak **keys**, strong values, and the classic leak where the value references
       the key and nothing is ever collected. Entries are removed lazily, on access, not eagerly at
       GC. `[TRAP]` `[X-REF 02]` `[PROVE]`
1.13.7 The canonical legitimate uses: `WeakHashMap` for metadata attached to foreign objects,
       `ThreadLocal.ThreadLocalMap`'s weak keys, class-metadata caches keyed by `Class`.
       `[X-REF 05]`
1.13.8 `ThreadLocalMap`'s weak key / strong value asymmetry as the precise mechanism of the
       ThreadLocal leak on pooled threads. `[X-REF 05]` `[PROVE]`
1.13.9 The reference-processing phase of GC: discovery during marking, then a per-strength pass
       (soft → weak → final → phantom) with `-XX:+ParallelRefProcEnabled` controlling parallelism.
       Visible as `Reference Processing` in the pause breakdown. `[DUMP]` `[RESEARCH]`
1.13.10 **Finalization**: `Object.finalize` runs on the single `Finalizer` thread, at an
        unpredictable time, possibly never, and delays reclamation by **at least one extra GC
        cycle** (the object must be marked finalizable, queued, run, then re-collected). `[PROVE]`
        `[NUM]`
1.13.11 The three ways finalization fails in production: the `Finalizer` queue backs up under load
        and the heap fills with finalizable garbage; an exception in `finalize` is swallowed
        silently; and object **resurrection** (storing `this` in a static during `finalize`) makes
        the object live again, exactly once. `[TRAP]` `[PROVE]`
1.13.12 Finalization deprecated for removal in Java 9, **disabled by default in Java 18** via
        `--finalization=disabled` (JEP 421), removal pending. `[VERSION-TRAP]` `[FLAG]`
        `[RESEARCH]`
1.13.13 `java.lang.ref.Cleaner` (Java 9) as the replacement: `Cleaner.create()`,
        `cleaner.register(obj, runnable)`, the cleaning thread, and the **hard rule** that the
        cleaning `Runnable` must not capture a reference to the registered object or nothing is
        ever collected. `[TRAP]` `[BUILD]` `[SOURCE]`
1.13.14 `Cleaner` is still a safety net, not a resource-management strategy —
        **try-with-resources / `AutoCloseable` is the strategy**, and the `Cleaner` exists only for
        the case where the caller forgot. `[X-REF 03]` `[TRAP]`
1.13.15 `jdk.internal.ref.Cleaner` and `DirectByteBuffer`: a direct buffer's native memory is freed
        only when the buffer object is collected, which is why direct-memory exhaustion happens with
        a mostly-empty heap and why NIO calls `System.gc()` in `Bits.reserveMemory`. `[PROVE]`
        `[TRAP]` `[RESEARCH]`
1.13.16 `-XX:+DisableExplicitGC` therefore **breaks** direct-buffer reclamation unless you also set
        `-XX:+ExplicitGCInvokesConcurrent`. A genuine production footgun. `[FLAG]` `[TRAP]`
        `[RESEARCH]`
1.13.17 Observability: `jdk.FinalizerStatistics` JFR event, `jcmd GC.finalizer_info`, and the
        `java.lang.ref.Finalizer` instance count in a heap histogram as the tell. `[DUMP]`
1.13.18 The decision table: strong / soft / weak / phantom / `Cleaner` / `AutoCloseable` — what each
        is for and the failure mode of using the wrong one. `[NUM]`

*(18 leaves)*

## §1.14 Memory outside the heap

1.14.1 The complete non-heap inventory: metaspace, compressed class space, code cache, thread
       stacks, GC internal structures (card tables, remembered sets, mark bitmaps), direct
       `ByteBuffer`s, mapped `ByteBuffer`s, JNI/FFM allocations, the symbol and string tables,
       JIT compiler scratch (arenas), JFR buffers, and glibc malloc arenas. `[NUM]`
1.14.2 **Metaspace** replaced PermGen in Java 8 (JEP 122) and lives in **native** memory, growing
       dynamically unless capped. `[VERSION-TRAP]` `[NUM]`
1.14.3 Why PermGen died: a fixed-size region sized in advance for something (class metadata) whose
       size nobody could predict, producing `OutOfMemoryError: PermGen space` on every redeploy.
       `[PROVE]`
1.14.4 What metaspace holds: `Klass` structures, method metadata and bytecode, constant pools,
       annotations, method counters, and vtables/itables. What it does *not* hold: `Class` objects
       (heap), interned strings (heap since Java 7), static field values (heap, in the mirror).
       `[TRAP]` `[NUM]`
1.14.5 The metaspace flag surface: `-XX:MetaspaceSize` (the *first GC trigger*, not the initial
       size — a widely misread flag), `-XX:MaxMetaspaceSize` (unbounded by default),
       `-XX:MinMetaspaceFreeRatio` (40), `-XX:MaxMetaspaceFreeRatio` (70),
       `-XX:CompressedClassSpaceSize` (1 GB reserved). `[FLAG]` `[NUM]` `[TRAP]` `[RESEARCH]`
1.14.6 **Always set `-XX:MaxMetaspaceSize` in a container**, because uncapped metaspace turns a
       class leak into an OOMKill with no Java-level error. `[TRAP]` `[X-REF 19]`
1.14.7 Metaspace leaks come from **classes**, not objects: repeated redeployment, dynamic proxy or
       bytecode generation in a loop (Groovy scripts compiled per request is the canonical one),
       and classloader leaks. `[TRAP]`
1.14.8 Observability: `jcmd VM.metaspace`, `jstat -gcmetacapacity`, `-Xlog:gc+metaspace=info`, and
       the `Metaspace` / `Class` categories in NMT. `[DUMP]`
1.14.9 The **code cache**: where JIT-compiled native code lives, `-XX:ReservedCodeCacheSize` (default
       240 MB with tiered compilation, 48 MB without), `-XX:InitialCodeCacheSize`. `[FLAG]` `[NUM]`
       `[RESEARCH]`
1.14.10 **Segmented code cache** (JEP 197, Java 9): three heaps — non-nmethods (VM internal),
        profiled nmethods (C1, short-lived), non-profiled nmethods (C2, long-lived) — sized by
        `-XX:NonNMethodCodeHeapSize`, `-XX:ProfiledCodeHeapSize`, `-XX:NonProfiledCodeHeapSize`.
        `[FLAG]` `[RESEARCH]`
1.14.11 **Code cache full** is a *silent* failure: the JVM logs
        `CodeCache is full. Compiler has been disabled.`, disables the JIT, and the application
        quietly runs interpreted at a fraction of the speed with no exception anywhere. This is one
        of the nastiest production degradations in Java. `[TRAP]` `[DUMP]` `[PROVE]`
1.14.12 Its usual causes: a very large application, an aggressive agent instrumenting everything, or
        `-XX:-UseCodeCacheFlushing` combined with heavy deoptimisation churn. Diagnose with
        `jcmd Compiler.codecache`, `jcmd Compiler.CodeHeap_Analytics`, and
        `-XX:+PrintCodeCache`. `[FLAG]` `[DUMP]`
1.14.13 **Direct memory**: `ByteBuffer.allocateDirect`, off-heap, bounded by
        `-XX:MaxDirectMemorySize` (default = `-Xmx` when unset), freed only via the buffer's
        `Cleaner`. `OutOfMemoryError: Direct buffer memory` is its exhaustion. `[FLAG]` `[NUM]`
        `[TRAP]`
1.14.14 Why direct buffers exist: zero-copy I/O — the OS can DMA straight into them, whereas a heap
        buffer must be copied to a temporary direct buffer first (and the JDK caches one per thread
        for exactly that, which is itself an unbounded per-thread memory sink). `[PROVE]`
        `[RESEARCH]` `[TRAP]`
1.14.15 `jdk.nio.maxCachedBufferSize` as the bound on that per-thread cache — required tuning for
        Netty-style workloads with many threads. `[FLAG]` `[RESEARCH]`
1.14.16 Netty's pooled allocator and `io.netty.maxDirectMemory` / `-Dio.netty.noPreferDirect`, since
        Netty accounts for direct memory itself and its OOM message is not the JVM's. `[TRAP]`
        `[RESEARCH]`
1.14.17 Memory-mapped files (`FileChannel.map`, `MappedByteBuffer`): counted in RSS and in the
        container's memory cgroup, not in `-Xmx`, and unmapped only on GC before Java 21's
        `Arena`-based `FileChannel.map(..., Arena)`. `[TRAP]` `[RESEARCH]`
1.14.18 JNI and FFM allocations: invisible to NMT unless the library cooperates, and the usual
        culprit when NMT-committed and RSS diverge. `[X-REF §3.22]`
1.14.19 GC's own structures: card table (~0.2% of heap), G1 remembered sets (up to ~10% historically),
        mark bitmaps (ZGC ~3%), forwarding tables. Budget them. `[NUM]` `[RESEARCH]`
1.14.20 **glibc malloc arenas**: up to `8 × ncpu` arenas each holding freed memory, producing an
        RSS that exceeds NMT-committed by hundreds of MB. Mitigations:
        `MALLOC_ARENA_MAX=2`, `jcmd System.trim_native_heap` (Linux, Java 18+), or switching to
        jemalloc/tcmalloc. `[TRAP]` `[NUM]` `[RESEARCH]`
1.14.21 The **NMT categories** you will actually read: Java Heap, Class, Thread, Thread Stack, Code,
        GC, GCCardSet, Compiler, Internal, Other, Symbol, Native Memory Tracking, Arena Chunk,
        Logging, Arguments, Module, Safepoint, Synchronization, Serviceability, Metaspace,
        String Deduplication, Object Monitors. `[DUMP]` `[RESEARCH]`
1.14.22 `reserved` versus `committed` in NMT, and why reserved is address space (harmless) while
        committed is what the kernel can charge you for. `[TRAP]` `[NUM]`

*(22 leaves)*

## §1.15 The failure taxonomy — OOM and friends

1.15.1 **Read the text after the colon before theorising.** The message names the subsystem that
       failed, and each has a different diagnosis. `[TRAP]`
1.15.2 `java.lang.OutOfMemoryError: Java heap space` — heap full, GC cannot reclaim. Leak,
       undersized heap, unbounded cache or queue, or a genuine spike.
1.15.3 `GC overhead limit exceeded` — >98% of time in GC recovering <2% of the heap, over 5
       consecutive full GCs. It is the *last warning before* heap space, and it is switched off by
       `-XX:-UseGCOverheadLimit`. `[NUM]` `[FLAG]`
1.15.4 `Metaspace` / `Compressed class space` — class metadata exhausted. Classloader leak or
       dynamic class generation.
1.15.5 `Direct buffer memory` — `MaxDirectMemorySize` reached, usually Netty/NIO buffers not
       released.
1.15.6 `unable to create new native thread` — OS thread limit or native memory exhausted, not a heap
       problem. `[TRAP]`
1.15.7 `Requested array size exceeds VM limit` — an array larger than ~`Integer.MAX_VALUE - 8`; a
       bug in size arithmetic, never a tuning issue. `[NUM]`
1.15.8 `Out of swap space?` — the OS could not satisfy a native allocation; look for a native leak
       or overcommit misconfiguration.
1.15.9 `Compressed class space` as its own distinct message, separate from `Metaspace`. `[TRAP]`
1.15.10 `reason stack_trace_with_native_method` — the allocation failed in native code.
        `[RESEARCH]`
1.15.11 **`OutOfMemoryError` kills only the thread that hit it.** Other threads continue in a
        degraded, partially-initialised world, which is why a JVM that "OOMed an hour ago" produces
        bizarre unrelated errors. `[TRAP]` `[PROVE]`
1.15.12 The two flags that must be on in every production JVM, and why:
        `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/dumps/` (evidence — an OOM without a
        dump means guessing) and `-XX:+ExitOnOutOfMemoryError` (kill the process rather than leave a
        half-dead JVM whose health check still passes). `[FLAG]`
1.15.13 `-XX:+CrashOnOutOfMemoryError` versus `-XX:+ExitOnOutOfMemoryError` versus
        `-XX:OnOutOfMemoryError="cmd"`: dump-and-crash, clean exit, or run a hook. The hook
        variant forks a process from a JVM that just failed to allocate — know why that is risky.
        `[FLAG]` `[TRAP]` `[RESEARCH]`
1.15.14 **OOMKilled versus OutOfMemoryError**, the distinction that is constantly conflated:
        `OutOfMemoryError` is thrown by the JVM with a stack trace and possibly a heap dump;
        **OOMKilled** (exit code 137, `Reason: OOMKilled` in `kubectl describe pod`) is the Linux
        kernel killing the process for exceeding its memory cgroup — no stack trace, no dump, no
        Java log line, only a `dmesg` entry. `[TRAP]` `[X-REF 11]` `[X-REF 19]`
1.15.15 Exit code 137 = 128 + 9 (SIGKILL); 143 = 128 + 15 (SIGTERM, a normal shutdown). Reading exit
        codes is the first step, not the last. `[NUM]` `[X-REF 11]`
1.15.16 The **hs_err_pid<pid>.log** crash file: its sections in order — the signal and instruction,
        the failing thread and its stack, all threads, VM state, mutexes, heap and metaspace
        summary, the code cache, the compilation events, the GC heap history, the full flag list,
        the environment, and `/proc/meminfo`. Reading it is a distinguishing skill. `[DUMP]`
        `[RESEARCH]`
1.15.17 `-XX:ErrorFile=/var/dumps/hs_err_%p.log` so the crash file is not written to a
        read-only working directory and lost. `[FLAG]` `[TRAP]`
1.15.18 `SIGSEGV` in a JVM is usually *not* a JVM bug: JNI code, a broken agent, or hardware. But
        `EXCEPTION_ACCESS_VIOLATION` inside compiled code with a reproducible frame is worth a bug
        report — and `-XX:-UseCompiler`/`-XX:CompileCommand=exclude` is the bisection tool.
        `[FLAG]` `[RESEARCH]`
1.15.19 The **failure decision tree**: process gone with no logs → OOMKilled or SIGKILL; process gone
        with `hs_err` → crash; `OutOfMemoryError` in logs → read the subsystem; slow but alive →
        GC, code cache, lock contention or downstream. `[PROVE]`

*(19 leaves)*

## §1.16 JIT compilation — the model

1.16.1 The core bargain: interpret first (fast to start, slow to run), compile later (slow to
       compile, fast to run), and use *measured* profile data a static compiler never has.
       `[PROVE]`
1.16.2 The five compilation levels HotSpot actually uses: **0** interpreter, **1** C1 without
       profiling (trivial methods, terminal), **2** C1 with invocation+backedge counters, **3** C1
       with full profiling, **4** C2. `[NUM]` `[SOURCE]` `[RESEARCH]`
1.16.3 The common path is 0 → 3 → 4; 0 → 1 for trivial methods; 0 → 2 → 3 → 4 when the C2 queue is
       long. Naming level 2's role (a faster stopgap when C2 is backed up) is the detail that shows
       you have read the policy. `[PROVE]` `[RESEARCH]`
1.16.4 The compilation trigger predicate, verbatim:
       `i > TierXInvocationThreshold * s || (i > TierXMinInvocationThreshold * s && i + b >
       TierXCompileThreshold * s)` where `i` = invocations, `b` = backedges, `s` = a scaling
       coefficient based on compile-queue length. `[SOURCE]` `[NUM]` `[PROVE]` `[RESEARCH]`
1.16.5 The default thresholds: `Tier3InvocationThreshold=200`, `Tier3MinInvocationThreshold=100`,
       `Tier3CompileThreshold=2000`, `Tier4InvocationThreshold=5000`,
       `Tier4MinInvocationThreshold=600`, `Tier4CompileThreshold=15000`; and in non-tiered mode
       `-XX:CompileThreshold=10000`. `[FLAG]` `[NUM]` `[RESEARCH]`
1.16.6 **Trap:** "methods compile after 10 000 invocations." That is the *non-tiered* C2 threshold,
       and tiered compilation (on by default since Java 8) **ignores `CompileThreshold` entirely**.
       `[TRAP]` `[VERSION-TRAP]`
1.16.7 **OSR** (on-stack replacement): a long-running loop is compiled and execution transfers into
       the compiled version *mid-method*, which is why a `main` with one hot loop gets fast without
       ever being re-invoked. OSR compilations appear with a `%` in `-XX:+PrintCompilation`.
       `[PROVE]` `[DUMP]` `[RESEARCH]`
1.16.8 The compiler threads: `-XX:CICompilerCount` (default 3 minimum with tiered: 1 C1 + 2 C2,
       scaled by CPU count), the compile queue, and why compilation competes with your application
       for CPU during startup. `[FLAG]` `[NUM]` `[RESEARCH]`
1.16.9 The optimisation inventory C2 performs, each by name: method inlining, virtual-call
       devirtualisation (monomorphic and bimorphic), profile-guided branch elimination, escape
       analysis and scalar replacement, lock elision and lock coarsening, loop unrolling, loop
       peeling and unswitching, range-check elimination, vectorisation (superword),
       common-subexpression elimination, dead-code elimination, constant folding of trusted final
       fields, null-check elision via implicit traps, and intrinsics. `[RESEARCH]`
1.16.10 **Inlining** as the enabling optimisation: it is not primarily about call overhead, it is
        about creating a larger scope in which every other optimisation can work. `[PROVE]`
1.16.11 The inlining budget flags: `-XX:MaxInlineSize` (35 bytecodes, for cold methods),
        `-XX:FreqInlineSize` (325 bytecodes, for hot methods), `-XX:InlineSmallCode` (2500 bytes of
        compiled callee), `-XX:MaxInlineLevel` (15 since Java 14, was 9),
        `-XX:MaxTrivialSize` (6). `[FLAG]` `[NUM]` `[RESEARCH]`
1.16.12 The practical consequence: a method over ~325 bytecodes is never inlined into a hot caller,
        which is a real argument for small methods that has nothing to do with readability.
        `[PROVE]` `[NUM]`
1.16.13 **Monomorphic / bimorphic / megamorphic** call sites: one observed receiver type → inline
        with a guard; two → inline both with a type switch; three or more → give up and do a real
        vtable/itable call. This is why a hot interface with many implementations is slow and a hot
        interface with one is free. `[PROVE]` `[NUM]` `[RESEARCH]`
1.16.14 **Deoptimisation**: when a speculative assumption is invalidated (a new subclass is loaded, a
        never-taken branch is taken, a null appears), the compiled frame is discarded and execution
        resumes in the interpreter at the same bytecode index. The compiled code is made
        not-entrant and eventually zombie/unloaded. `[PROVE]`
1.16.15 **Uncommon traps** as the mechanism: the compiler emits a trap instead of code for a path it
        believes unreachable, which is what makes profile-guided elimination sound. Reasons include
        `class_check`, `null_check`, `unstable_if`, `unloaded`, `bimorphic`, `range_check`.
        `[SOURCE]` `[RESEARCH]`
1.16.16 **Deoptimisation storms**: a rarely-taken path taken repeatedly causes repeated
        deopt/recompile cycles, burning CPU in the compiler threads. Visible in
        `-XX:+UnlockDiagnosticVMOptions -XX:+LogCompilation` and in JFR's `jdk.Deoptimization`
        event. `[TRAP]` `[DUMP]` `[RESEARCH]`
1.16.17 `-XX:PerMethodRecompilationCutoff` and `-XX:PerBytecodeRecompilationCutoff` as the
        "make it not-compilable" backstops after too many recompiles. `[FLAG]` `[RESEARCH]`
1.16.18 **Escape analysis**: an object proven not to escape a method can be scalar-replaced (its
        fields become registers/locals), stack-allocated conceptually, and its locks elided.
        `-XX:+DoEscapeAnalysis` (on), `-XX:+EliminateAllocations` (on),
        `-XX:+EliminateLocks` (on). `[FLAG]` `[PROVE]`
1.16.19 **Trap:** "escape analysis puts objects on the stack." HotSpot does **scalar replacement**,
        not stack allocation — the object never exists at all. And it is all-or-nothing per
        allocation site, defeated by anything that makes the object escape (including storing it in
        a field or passing it to a non-inlined method). Partial escape analysis exists in Graal, not
        C2. `[TRAP]` `[PROVE]` `[RESEARCH]`
1.16.20 **Intrinsics**: methods the JIT replaces with hand-written machine code rather than compiling
        their Java body — `Math.min/max/sqrt/abs`, `System.arraycopy`, `Object.hashCode`,
        `String.indexOf`/`equals`/`compareTo`, `Arrays.equals`/`mismatch`, `Integer.bitCount`
        (POPCNT), `Long.numberOfLeadingZeros`, `Thread.onSpinWait`, `VarHandle` and atomic
        operations, and the `@IntrinsicCandidate` annotation that marks them. `[SOURCE]` `[ASM]`
        `[RESEARCH]`
1.16.21 `-XX:+PrintCompilation` output read column by column: timestamp, compile id, the flags
        (`%` OSR, `s` synchronized, `!` has exception handlers, `b` blocking, `n` native), tier,
        method, size, and `made not entrant` / `made zombie`. `[FLAG]` `[DUMP]`
1.16.22 `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` and what "too big", "hot method too big",
        "callee is too large", "not inlineable" and "recursive inlining too deep" each mean.
        `[FLAG]` `[DUMP]` `[RESEARCH]`
1.16.23 `-XX:CompileCommand=` (`print`, `exclude`, `inline`, `dontinline`, `compileonly`,
        `quiet`, `option`) and `-XX:CompilerDirectivesFile` as the surgical instruments for
        bisecting a JIT problem. `[FLAG]` `[RESEARCH]`
1.16.24 **Warmup** as the direct consequence of the whole model: the first thousands of executions
        run interpreted or C1. Real implications — the first requests after a deploy are slow, a
        health check that passes instantly sends full traffic to a cold JVM, benchmarks without
        warmup measure the interpreter, and canaries should ramp rather than switch. `[PROVE]`
1.16.25 `-XX:-TieredCompilation` (C2 only: slower warmup, marginally better peak) and
        `-XX:TieredStopAtLevel=1` (C1 only: fast warmup, no peak — the right answer for short-lived
        CLI tools and some tests). `[FLAG]` `[PROVE]`
1.16.26 GraalVM's JIT as a C2 replacement (`-XX:+UseJVMCICompiler`), and the JVMCI interface (JEP
        243) that makes a compiler written in Java possible. `[RESEARCH]`

*(26 leaves)*

## §1.17 Safepoints, handshakes and VM operations

1.17.1 A **safepoint** is a point in execution where every thread's stack is walkable and every oop
       is precisely known. GC, deoptimisation, biased-lock revocation, thread dumps, heap dumps and
       class redefinition all require one. `[PROVE]`
1.17.2 Safepoint **polls** are inserted by the JIT at method returns and loop backedges (uncounted
       loops always; counted `int` loops historically not, which is the classic long-TTSP cause).
       The poll is a load from a page the VM can make unreadable, so the fast path costs one
       instruction. `[ASM]` `[PROVE]` `[RESEARCH]`
1.17.3 **Time-to-safepoint (TTSP)** is *not* the pause duration and is invisible in GC logs. A
       10 ms GC with a 900 ms TTSP is a 910 ms pause that the GC log reports as 10 ms. `[TRAP]`
       `[NUM]` `[PROVE]`
1.17.4 The classic long-TTSP causes: a counted loop with no poll, a huge `System.arraycopy` or array
       fill, a JNI call that will not return, page faults on a swapped-out stack, and thousands of
       threads to bring in. `[TRAP]` `[RESEARCH]`
1.17.5 Threads in **native** code (JNI, blocking syscalls) are already safepoint-safe and do not need
       to be stopped; they block on return instead. `[PROVE]`
1.17.6 `-Xlog:safepoint*` and `-Xlog:safepoint+stats` read line by line:
       `Reaching safepoint`, `At safepoint`, `Total time for which application threads were stopped`
       and `Stopping threads took`. The second number is TTSP. `[FLAG]` `[DUMP]`
1.17.7 `-XX:+SafepointTimeout -XX:SafepointTimeoutDelay=<ms>` to name the thread that is late.
       `[FLAG]` `[RESEARCH]`
1.17.8 `-XX:GuaranteedSafepointInterval` (default 1000 ms) means the JVM stops the world roughly
       once a second even with no GC, for cleanup VM operations. Setting it to 0 requires
       `-XX:+UnlockDiagnosticVMOptions`. `[FLAG]` `[NUM]` `[TRAP]` `[RESEARCH]`
1.17.9 **Thread-local handshakes** (JEP 312, Java 10): a callback executed per-thread without a
       global safepoint, implemented by an indirection through a per-thread polling-page pointer.
       This is what made cheap per-thread stack sampling and biased-lock revocation-without-STW
       possible. `[SOURCE]` `[RESEARCH]`
1.17.10 The **VM operation** queue and `VMThread`: operations are enqueued and executed at a
        safepoint. Named operations worth recognising in logs: `G1CollectForAllocation`,
        `ParallelGCFailedAllocation`, `RevokeBias` (gone with biased locking), `ThreadDump`,
        `HeapDumper`, `PrintThreads`, `GetAllStackTraces`, `ICBufferFull`, `Deoptimize`,
        `EnableBiasedLocking`, `Cleanup`, `RedefineClasses`. `[DUMP]` `[RESEARCH]`
1.17.11 Non-GC safepoints that surprise people: `jstack`/`Thread.getAllStackTraces` (a full STW),
        heap dumps, class redefinition by an agent, and `ICBufferFull` from inline-cache churn.
        `[TRAP]`
1.17.12 **Safepoint bias in profilers**: a sampling profiler built on `getAllStackTraces` can only
        sample *at* safepoints, so it systematically misattributes time to methods near poll sites.
        This is the entire reason async-profiler exists. `[PROVE]` `[TRAP]` `[RESEARCH]`
1.17.13 `-XX:+DebugNonSafepoints` to make compiled-code debug info available between safepoints, so
        AsyncGetCallTrace-based profilers get accurate line numbers. `[FLAG]` `[RESEARCH]`
1.17.14 Safepoints and virtual threads: a mounted virtual thread's carrier is what reaches the
        safepoint, and an unmounted one is a heap object with no stack to walk — which is exactly
        why `jstack` does not show virtual threads. `[X-REF 05]` `[RESEARCH]`
1.17.15 Biased locking's `RevokeBias` safepoint as the historical example of a non-GC safepoint that
        dominated some workloads, and JEP 374 (Java 15) disabling biased locking partly because of
        it. `[X-REF 05]` `[RESEARCH]`
1.17.16 The full accounting: application pause time = Σ(TTSP + safepoint operation time) over all
        safepoints, GC and non-GC alike. Measure it with `-Xlog:safepoint`, not with the GC log.
        `[PROVE]` `[NUM]`

*(16 leaves)*

## §1.18 JVM startup, shutdown and the flag surface

1.18.1 The startup sequence in order: `java` launcher → create the VM (`JNI_CreateJavaVM`) → parse
       arguments and apply ergonomics → reserve the heap → initialise the GC → create the bootstrap
       loader → initialise `java.lang` core classes → create the main thread → load the main class
       → run `<clinit>` → invoke `main`. `[SOURCE]` `[RESEARCH]`
1.18.2 Ergonomics: the JVM chooses collector, heap size, GC thread counts and compiler thread counts
       from CPU count and memory. Print the outcome with
       `java -XX:+PrintFlagsFinal -version`, and the difference from defaults with
       `-XX:+PrintCommandLineFlags`. `[FLAG]` `[DUMP]`
1.18.3 The three flag categories: `-X` (non-standard but stable), `-XX:` (implementation-specific),
       and standard `-` options. `-XX:+Flag` / `-XX:-Flag` for booleans, `-XX:Flag=value` for the
       rest. `[NUM]`
1.18.4 Flag lifecycle words that appear in warnings: `product`, `diagnostic` (needs
       `-XX:+UnlockDiagnosticVMOptions`), `experimental` (needs `-XX:+UnlockExperimentalVMOptions`),
       `develop` (debug builds only), `deprecated`, `obsolete` (accepted and ignored), `expired`
       (rejected). `[RESEARCH]`
1.18.5 `JAVA_TOOL_OPTIONS`, `JDK_JAVA_OPTIONS` (Java 9+, `java` launcher only) and `_JAVA_OPTIONS`
       — the environment variables that inject flags behind your back, and their precedence.
       `[TRAP]` `[RESEARCH]`
1.18.6 `@argfiles` for very long command lines, and `--enable-preview` requiring matching compile and
       run versions. `[FLAG]`
1.18.7 A **baseline production flag set** to defend in an interview, each line justified:
       `-Xms=-Xmx`, `-XX:MaxRAMPercentage`, `-XX:MaxMetaspaceSize`, `-XX:+UseG1GC`,
       `-XX:MaxGCPauseMillis`, `-Xlog:gc*:file=...`, `-XX:+HeapDumpOnOutOfMemoryError`,
       `-XX:HeapDumpPath`, `-XX:+ExitOnOutOfMemoryError`, `-XX:ErrorFile`,
       `-XX:NativeMemoryTracking=summary`, `-XX:StartFlightRecording=...`,
       `-Djava.security.egd=file:/dev/urandom` (or `-Djava.security.properties` for the modern
       equivalent). `[FLAG]` `[PROVE]`
1.18.8 The anti-flag list: `-XX:+UseGCOverheadLimit` disabled, `-Xverify:none`, `-XX:+AggressiveOpts`
       (removed in 12), `-XX:+UseConcMarkSweepGC` (removed in 14), `-XX:PermSize` (removed in 8),
       `-XX:+UseBiasedLocking` (disabled 15, removed 18) — all of which appear in copy-pasted
       start scripts and either fail to start the JVM or do nothing. `[TRAP]` `[VERSION-TRAP]`
       `[RESEARCH]`
1.18.9 Runtime flag changes: `jcmd VM.set_flag` for the (small) set of manageable flags, and
       `jinfo -flag` for reading. Most flags are *not* changeable at runtime. `[TRAP]` `[DUMP]`
1.18.10 Shutdown: `System.exit(int)` → shutdown hooks run concurrently in unspecified order →
        `Runtime.halt` skips hooks entirely → `SIGTERM` triggers the same hook path → `SIGKILL`
        runs nothing. `[X-REF 05]` `[X-REF 11]`
1.18.11 `Runtime.getRuntime().addShutdownHook(Thread)`: no ordering guarantee, no time limit
        (so a hung hook hangs the shutdown until the orchestrator sends SIGKILL), and no execution
        on `halt`. Spring Boot's graceful shutdown is built on one. `[TRAP]` `[X-REF 07]`
1.18.12 The Kubernetes interaction: SIGTERM → `terminationGracePeriodSeconds` (default 30) →
        SIGKILL. A shutdown hook that drains connections must finish inside that window.
        `[X-REF 19]` `[NUM]`
1.18.13 The JVM exits when the last **non-daemon** thread dies, not when `main` returns.
        `[X-REF 05]` `[TRAP]`
1.18.14 **CDS** (class data sharing): the JDK ships a default archive (`classes.jsa`) covering core
        JDK classes, mapped shared and pre-parsed at startup. `-Xshare:auto|on|off`,
        `-XX:SharedArchiveFile`. `[FLAG]` `[RESEARCH]`
1.18.15 **AppCDS** and **dynamic CDS** (JEP 350, Java 13): `-XX:ArchiveClassesAtExit=app.jsa` to
        record on exit, `-XX:SharedArchiveFile=app.jsa` to use it. Typical startup improvement
        10–30% for a Spring Boot app. `[FLAG]` `[NUM]` `[RESEARCH]`
1.18.16 **The Leyden AOT cache** (JEP 483, Java 24) stores classes already *loaded and linked*, not
        merely parsed; JEP 514 (Java 25) collapses the two-step training run into
        `-XX:AOTCacheOutput`/`-XX:AOTCache`; JEP 515 adds AOT **method profiles** so the JIT starts
        optimising immediately. Reported startup improvements up to ~40%. This supersedes the
        "CDS is the startup answer" framing. `[VERSION-TRAP]` `[NUM]` `[RESEARCH]`
1.18.17 **GraalVM native image** as the other end of the spectrum: closed-world static analysis,
        ahead-of-time compilation to a native binary, ~0.02–0.4 s startup and ~40% of the RSS, at
        the cost of build time, reduced peak throughput on long-running CPU-bound work, and
        explicit configuration for reflection, proxies, resources and serialization. `[NUM]`
        `[RESEARCH]`
1.18.18 **CRaC** (coordinate restore at checkpoint) as the third option: checkpoint a warmed JVM,
        restore in milliseconds. Trade-offs: open file descriptors and sockets must be closed and
        reopened via the `Resource` API, and the checkpoint contains secrets. `[RESEARCH]`
1.18.19 The startup-strategy decision table: plain JVM / CDS / AppCDS / AOT cache / CRaC / native
        image, scored on startup, warmup, peak throughput, footprint, build complexity, and dynamic
        feature support. `[NUM]` `[PROVE]`
1.18.20 `jlink` and `jdeps` to build a minimal runtime image, and why that reduces container size and
        class-loading surface but does **not** reduce warmup. `[TRAP]` `[X-REF 19]`

*(20 leaves)*

## §1.19 The memory model at implementation level

1.19.1 The JMM is a *language* contract (JLS 17); this section is only the **implementation** side —
       what HotSpot emits to satisfy it. Full treatment of happens-before, `volatile` semantics,
       safe publication and final-field freeze is in `05-multithreading-concurrency.md`.
       `[X-REF 05]`
1.19.2 The four barrier categories the JSR-133 cookbook names — LoadLoad, LoadStore, StoreStore,
       StoreLoad — and the rule that only StoreLoad is expensive on x86. `[X-REF 05]` `[PROVE]`
1.19.3 What HotSpot actually emits on x86-64: a `volatile` read is a plain `mov`; a `volatile` write
       is `mov` followed by `lock addl $0,(%rsp)` (a StoreLoad fence). On AArch64: `ldar` / `stlr`.
       `[ASM]` `[NUM]` `[RESEARCH]`
1.19.4 Why the same code passes on x86 and fails on Graviton/Apple silicon: x86-TSO forbids most
       reorderings for free; AArch64 does not. "It works on my machine" often means "my machine has
       a stronger memory model". `[PROVE]` `[X-REF 05]`
1.19.5 The **JIT** is a reordering source at least as aggressive as the CPU: hoisting a non-volatile
       read out of a loop turns a missing-`volatile` stop flag into an infinite loop, reproducibly.
       `[PROVE]` `[ASM]` `[X-REF 05]`
1.19.6 The final-field **freeze** as an emitted StoreStore barrier at the end of a constructor, and
       why it costs nothing on x86. `[X-REF 05]` `[ASM]`
1.19.7 The class-initialisation lock (JVMS 5.5) as the JVM-level synchronization primitive that the
       holder idiom relies on, with no user-visible lock at all. `[X-REF 05]` `[PROVE]`
1.19.8 Monitor implementation at the header level — the mark word states, stack locking, inflation to
       an `ObjectMonitor` — stated in one paragraph here because §1.10.3 already introduced the mark
       word, with the full treatment in guide 05. `[X-REF 05]`
1.19.9 Biased locking's rise and removal (JEP 374, disabled 15, removed 18) as a JVM-implementation
       story: it optimised uncontended locking at the cost of `RevokeBias` safepoints, and modern
       workloads made that trade bad. `[X-REF 05]` `[VERSION-TRAP]` `[RESEARCH]`
1.19.10 GC and the memory model: a moving collector rewrites every reference in the heap and in every
        thread's stack while the program is "stopped", which is only sound because of precise oop
        maps at safepoints. `[PROVE]`
1.19.11 Object initialisation ordering at the JVM level: allocate (zeroed) → run `<init>` →
        publish the reference. The publication store can be reordered with the constructor's stores
        unless a barrier says otherwise, which is the unsafe-publication mechanism. `[X-REF 05]`
        `[PROVE]`
1.19.12 `jcstress` as the JDK's own litmus-test harness for the JMM, and the honest framing that
        application developers verify with it, never reason with it. `[X-REF 05]` `[RESEARCH]`

*(12 leaves)*

## §1.20 The diagnostic toolchain — the inventory

1.20.1 `jps -lvm` — running JVMs, PIDs, main classes and flags. First command, always.
1.20.2 `jcmd <pid> help` — **the modern superset**; the others are effectively legacy aliases. Learn
       this one and you have learned the rest. `[DUMP]`
1.20.3 The jcmd command inventory grouped by purpose: `VM.version`, `VM.info`, `VM.flags`,
       `VM.command_line`, `VM.system_properties`, `VM.uptime`, `VM.dynlibs`, `VM.set_flag`,
       `VM.native_memory`, `VM.metaspace`, `VM.classloaders`, `VM.classloader_stats`,
       `VM.class_hierarchy`, `VM.stringtable`, `VM.symboltable`, `VM.systemdictionary`,
       `Thread.print`, `Thread.dump_to_file`, `GC.run`, `GC.heap_info`, `GC.heap_dump`,
       `GC.class_histogram`, `GC.class_stats`, `GC.finalizer_info`, `Compiler.codecache`,
       `Compiler.codelist`, `Compiler.queue`, `Compiler.CodeHeap_Analytics`,
       `Compiler.directives_add`, `JFR.start`, `JFR.dump`, `JFR.stop`, `JFR.check`,
       `JFR.configure`, `JVMTI.agent_load`, `ManagementAgent.start`,
       `System.trim_native_heap`, `System.native_heap_info`. `[DUMP]` `[RESEARCH]`
1.20.4 `jstack <pid>` — thread dump: every thread's stack, state, `nid`, held and awaited locks, plus
       explicit deadlock detection. `-l` for lock info, `-F` to force. `[DUMP]` `[X-REF 05]`
1.20.5 `jcmd <pid> Thread.dump_to_file -format=json` (Java 21) — the only dump that includes
       **virtual threads**, grouped by `StructuredTaskScope`. `[VERSION-TRAP]` `[X-REF 05]`
       `[RESEARCH]`
1.20.6 `jmap -histo:live <pid>` — live object histogram (count, bytes, class). Note that `:live`
       forces a full GC. `[TRAP]` `[DUMP]`
1.20.7 `jmap -dump:live,format=b,file=heap.hprof <pid>` / `jcmd GC.heap_dump` — the heap dump.
       Pauses the JVM for roughly the live-set walk and writes a file roughly heap-sized. `[TRAP]`
       `[NUM]`
1.20.8 `jstat` and its options: `-gcutil` (percent utilisation of each space plus GC counts and
       times), `-gc`, `-gccapacity`, `-gcnew`, `-gcold`, `-gcmetacapacity`, `-class`,
       `-compiler`, `-printcompilation`. `jstat -gcutil <pid> 1s` is the fastest live GC read there
       is. `[DUMP]`
1.20.9 `jinfo <pid>` — flags and system properties; `jinfo -flag +PrintGC <pid>` for the manageable
       ones. `[DUMP]`
1.20.10 `jhsdb` — the serviceability agent: `jhsdb jstack --core`, `jhsdb jmap`, `jhsdb clhsdb`,
        `jhsdb debugd`. The tool for a core file when the process is already dead. `[RESEARCH]`
1.20.11 `jfr` (the CLI): `jfr summary`, `jfr print --events <type>`, `jfr metadata` — reading a
        recording without opening JMC. `[DUMP]` `[RESEARCH]`
1.20.12 **JDK Flight Recorder**: always-on, <1% overhead at default settings, built into the JVM.
        `-XX:StartFlightRecording=duration=60s,filename=r.jfr,settings=profile` or
        `jcmd <pid> JFR.start`. The `default` and `profile` templates and the difference between
        them. `[FLAG]` `[NUM]` `[RESEARCH]`
1.20.13 The JFR event types you will actually use, by name: `jdk.ExecutionSample`,
        `jdk.NativeMethodSample`, `jdk.ObjectAllocationSample` (Java 16+, throttled: 150/s default,
        300/s profile), `jdk.ObjectAllocationInNewTLAB`, `jdk.ObjectAllocationOutsideTLAB`,
        `jdk.GarbageCollection`, `jdk.GCPhasePause`, `jdk.OldObjectSample` (the leak-detection
        event), `jdk.JavaMonitorEnter`, `jdk.JavaMonitorWait`, `jdk.ThreadPark`,
        `jdk.ThreadStart`, `jdk.SafepointBegin`, `jdk.ExecutionSample`, `jdk.Compilation`,
        `jdk.Deoptimization`, `jdk.CodeCacheFull`, `jdk.ClassLoad`, `jdk.SocketRead`,
        `jdk.FileWrite`, `jdk.ExceptionStatistics`, `jdk.VirtualThreadPinned`,
        `jdk.VirtualThreadStart`, `jdk.NativeMemoryUsage` (Java 24+). `[RESEARCH]` `[DUMP]`
1.20.14 Custom JFR events: `extends jdk.jfr.Event` with `@Name`, `@Label`, `@Category`,
        `@Enabled`, `@StackTrace`, `@Threshold`, plus `begin()`/`commit()`/`shouldCommit()`.
        `[BUILD]` `[RESEARCH]`
1.20.15 **JDK Mission Control** for reading recordings: the automated analysis page, the method
        profiling view, the TLAB allocation view, the GC view, and the "Live Object" leak view.
1.20.16 **Eclipse MAT** for heap dumps: histogram, **dominator tree**, **retained size** versus
        shallow size, **Leak Suspects**, **Path to GC Roots (exclude weak/soft)**, OQL, and the
        "unreachable objects" histogram. `[DUMP]`
1.20.17 **async-profiler**: sampling via `AsyncGetCallTrace` + POSIX signals, hence **no safepoint
        bias**; events `cpu`, `alloc`, `lock`, `wall`, `itimer`, `ctimer`, plus perf events;
        outputs flamegraph HTML, collapsed stacks, or JFR. Attach with
        `asprof -e cpu -d 30 -f out.html <pid>` or `-agentpath`. `[RESEARCH]`
1.20.18 Reading a **flame graph**: width = samples (time), y = stack depth, colour is arbitrary, and
        the plateaus are what matter. Differential flame graphs for before/after. `[PROVE]`
1.20.19 The rest of the ecosystem by name and purpose: VisualVM, JConsole, GCViewer/GCeasy for GC
        logs, `ycrash`/`fastthread` for dumps, Micrometer + Prometheus JVM metrics
        (`jvm_memory_used_bytes`, `jvm_gc_pause_seconds`, `jvm_threads_live`), Arthas, BTrace, JMX
        via `ManagementFactory` (`MemoryMXBean`, `ThreadMXBean`, `GarbageCollectorMXBean`,
        `RuntimeMXBean`, `HotSpotDiagnosticMXBean`). `[X-REF 20]` `[RESEARCH]`
1.20.20 `HotSpotDiagnosticMXBean.dumpHeap(path, live)` as the programmatic heap dump, and
        `ThreadMXBean.findDeadlockedThreads()` as the programmatic deadlock check. `[BUILD]`
        `[X-REF 05]`
1.20.21 Unified logging (`-Xlog`) as one tool covering all of the above subsystems: the
        `tag-selection:output:decorators:output-options` grammar. `[FLAG]` (detail in §2.3)
1.20.22 The tool-choice decision table: which tool answers which question, at what overhead, and
        whether it pauses the JVM. `[NUM]` `[PROVE]`
1.20.23 Container reality check: `jcmd` must run in the target's PID and mount namespace
        (`kubectl exec`, or `jcmd` from a debug sidecar with `shareProcessNamespace`), the JDK tools
        must exist in the image (a JRE-only image has none), and the attach mechanism uses
        `/tmp/.java_pid<pid>` — so a read-only `/tmp` breaks attach. `[TRAP]` `[X-REF 19]`
        `[RESEARCH]`

*(23 leaves)*

---

**PART 1 total: 15+28+24+20+25+16+20+20+20+23+26+27+18+22+19+26+16+20+12+23 = 420 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master memory-area table**: area, mandated by JVMS or HotSpot-specific, shared or
      per-thread, what it holds, which flag sizes it, which error it throws, and how you inspect it.
      One row per area from §1.8.1. `[NUM]`
2.1.2 **The master cost table**: allocation fast path (~1 ns), allocation slow path / TLAB refill,
      young GC per MB of live data, full GC per GB of live data, safepoint entry, class load +
      verify per class, interpreted vs C1 vs C2 execution speed ratio (roughly 1 : 5–10 : 20–50 for
      arithmetic-heavy code), volatile read vs write, uncontended lock, and a heap dump per GB.
      Amortised versus worst case split out on every row. `[NUM]` `[PROVE]`
2.1.3 **The master collector table** from §1.12.22, restated as the canonical version: pause
      profile, throughput cost, footprint cost, heap range, barrier type, compressed-oops support,
      generational, class unloading, availability by vendor, and the one-line "choose when".
      `[NUM]`
2.1.4 **The master OOM table** from §1.15: message text, subsystem, usual cause, first command to
      run, and the fix. `[NUM]`
2.1.5 **The master flag table**: the ~45 flags a backend engineer should recognise, grouped by
      subsystem, each with its default and one line of justification. `[FLAG]` `[NUM]`
2.1.6 **The master footprint table**: per-object header, per-array header, per-thread stack,
      per-class metaspace (~2–10 KB), per-compiled-method code cache, per-direct-buffer, per-region
      remembered set — the numbers you need to size a container from first principles. `[NUM]`
      `[PROVE]`
2.1.7 **The master tool table** from §1.20.22: question → tool → overhead → does it pause →
      output artifact.
2.1.8 **The master version table**: JDK 8 → 25, one row per release, listing only the JVM-internals
      changes (collectors, headers, class loading, JIT, tooling). `[VERSION-TRAP]`

*(8 leaves)*

## §2.2 GC selection and tuning as a procedure

2.2.1 The rule that precedes all tuning: **most "GC problems" are allocation problems or leaks.**
      Fix the allocation rate or the leak before touching a flag. `[PROVE]` `[TRAP]`
2.2.2 The measurement order: (1) enable GC logging, (2) get allocation rate, (3) get live-set size
      after full GC, (4) get pause distribution, (5) get GC CPU share. Only then choose.
      `[PROVE]`
2.2.3 Deriving heap size from the live set: a working rule is 2–3× the post-full-GC live set for
      G1, more for ZGC (concurrent collection needs headroom for floating garbage). `[NUM]`
      `[PROVE]`
2.2.4 Deriving young-gen size from allocation rate and the target young-GC interval. `[NUM]`
      `[PROVE]`
2.2.5 `-Xms` = `-Xmx` and why: no resize pauses, no heap-uncommit churn, RSS visible immediately
      instead of creeping, and predictable behaviour under a container limit. `[PROVE]`
2.2.6 Setting a *realistic* `MaxGCPauseMillis`: it is a soft goal, and setting it to 10 ms on G1
      makes G1 shrink the young gen until it collects constantly, destroying throughput and
      *raising* total pause time. `[TRAP]` `[PROVE]` `[NUM]`
2.2.7 The G1 tuning playbook by symptom: long young pauses → smaller young gen or fewer live
      objects; long mixed pauses → `G1MixedGCCountTarget` up, `G1MixedGCLiveThresholdPercent`
      down; full GCs → IHOP down or heap up; humongous allocations → region size up;
      to-space exhausted → `G1ReservePercent`/`G1HeapReservePercent` up or heap up. `[NUM]`
      `[PROVE]` `[RESEARCH]`
2.2.8 The ZGC tuning playbook: allocation stalls → more heap or more `ConcGCThreads`; high CPU →
      fewer `ConcGCThreads`; footprint → `SoftMaxHeapSize`. Almost nothing else. `[PROVE]`
2.2.9 When switching collectors is actually right, and the honest expectation: ZGC buys pause time
      and costs ~10–15% throughput and extra heap; Parallel buys throughput and costs pause
      predictability. Measure both under production-shaped load. `[NUM]` `[PROVE]`
2.2.10 The five common tuning mistakes, named: oversizing the heap blindly (longer full GCs, worse
       locality), ignoring allocation rate, switching collector before measuring, testing without
       production-shaped load, and tuning without reading a log. `[TRAP]` `[RESEARCH]`
2.2.11 **Trap:** "a bigger heap is always better." A bigger heap means longer full GCs, worse cache
       locality, more page-table pressure, and it hides leaks instead of fixing them. `[TRAP]`
       `[PROVE]`
2.2.12 **Trap:** "minor GC doesn't pause the application." It does; it is just short. `[TRAP]`
       `[RESEARCH]`
2.2.13 **Trap:** "Serial GC is for toy applications." For a 1-CPU, 512 MB container running a
       short-lived job, Serial beats G1 on both footprint and total time. `[TRAP]` `[RESEARCH]`
2.2.14 The GC-tuning goals you should state before touching anything: a throughput target
       (% of CPU in GC), a pause target (p99 and max), and a footprint target. Without all three,
       "tuned" is undefined. `[PROVE]`
2.2.15 The allocation-reduction levers that beat any flag: bounded caches, avoid boxing in hot
       paths, reuse buffers, stream instead of materialise, avoid `String` churn in logging
       (parameterised SLF4J, not concatenation), size collections up front. `[X-REF 02]`
       `[X-REF 20]`
2.2.16 Load testing GC properly: warm the JVM, run at production shape (not peak-only), run long
       enough to see at least several old-gen cycles, and compare *distributions*, not means.
       `[PROVE]`

*(16 leaves)*

## §2.3 Reading GC logs

2.3.1 Unified logging (JEP 158/271, Java 9) replaced `-XX:+PrintGCDetails` and friends. The grammar:
      `-Xlog:<what>:<output>:<decorators>:<output-options>`, where `what` is
      `tag1+tag2*=level`. `[VERSION-TRAP]` `[FLAG]`
2.3.2 The production-grade GC logging line, defended piece by piece:
      `-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags:filecount=5,filesize=20M`. It is nearly
      free and irreplaceable after an incident. `[FLAG]`
2.3.3 Useful tag selections beyond `gc*`: `gc+heap=debug`, `gc+humongous=debug`, `gc+age=trace`,
      `gc+ergo*=trace`, `gc+cpu`, `gc+ref`, `gc+metaspace`, `safepoint*`, `class+load=info`,
      `class+unload=info`, `jit+compilation=debug`, `os+container=trace`. `[FLAG]` `[RESEARCH]`
2.3.4 Decorators available: `time`, `uptime`, `timemillis`, `uptimemillis`, `timenanos`, `pid`,
      `tid`, `level`, `tags`. `[RESEARCH]`
2.3.5 Reading a G1 young pause line by line:
      `[3.456s][info][gc] GC(12) Pause Young (Normal) (G1 Evacuation Pause) 512M->48M(1024M) 8.234ms`
      — GC id, cause, before→after(total), duration. `[DUMP]` `[NUM]`
2.3.6 The GC **cause** vocabulary and what each tells you: `G1 Evacuation Pause`,
      `G1 Humongous Allocation`, `G1 Periodic Collection`, `GCLocker Initiated GC`,
      `Metadata GC Threshold`, `Ergonomics`, `Allocation Failure`, `System.gc()`,
      `Heap Inspection Initiated GC`, `Heap Dump Initiated GC`, `Concurrent Mark Cycle`.
      `[RESEARCH]` `[DUMP]`
2.3.7 The pause **breakdown** sub-lines and what a big one means: `Pre Evacuate Collection Set`,
      `Merge Heap Roots`, `Evacuate Collection Set` (Object Copy, Ext Root Scanning, Termination),
      `Post Evacuate Collection Set` (Reference Processing, Weak Processing, Redirty Cards, Free
      Collection Set). `[DUMP]` `[RESEARCH]`
2.3.8 `To-space exhausted` / `Evacuation Failure` in the log, and the multi-second pause that
      follows. The fix is headroom, not a smaller pause goal. `[TRAP]` `[DUMP]`
2.3.9 `Pause Full (Allocation Failure)` in a G1 log is an incident, not a routine event. `[TRAP]`
2.3.10 Reading `[gc,cpu] User=... Sys=... Real=...`: `Real` much greater than `User+Sys` means the
       JVM was descheduled or swapping, not that GC was slow. This is the single best line for
       spotting a CPU-throttled container. `[TRAP]` `[NUM]` `[PROVE]` `[X-REF 19]`
2.3.11 Reading `gc+age=trace` age histograms to diagnose premature promotion. `[DUMP]`
2.3.12 Computing the three headline numbers from a log by hand: allocation rate
       (Σ Eden freed ÷ elapsed), promotion rate, and GC CPU share (Σ pause × threads ÷ elapsed).
       `[NUM]` `[PROVE]`
2.3.13 The **leak signature** in a log: post-full-GC old-gen occupancy rising monotonically over
       hours. The **undersized-heap signature**: high but flat post-GC floor with frequent full GCs.
       The **spike signature**: floor returns to baseline. Distinguishing these three is the whole
       skill. `[PROVE]` `[DUMP]`
2.3.14 Tools that parse logs for you: GCViewer, GCeasy, `-Xlog:gc*` + a Prometheus exporter. Use
       them, but be able to read the raw log because the tool will be unavailable at 3 a.m.
2.3.15 GC logging overhead is negligible (a few hundred KB/hour and no measurable pause impact) —
       there is no defensible reason to run production without it. `[NUM]` `[PROVE]`
2.3.16 Rotating and shipping GC logs: `filecount`/`filesize`, and the fact that a container restart
       loses them unless the path is a mounted volume. `[TRAP]` `[X-REF 19]`

*(16 leaves)*

## §2.4 Sizing a JVM inside a container

2.4.1 Container awareness: since Java 10 (backported to 8u191) the JVM reads cgroup v1/v2 limits, so
      `Runtime.availableProcessors()` and default heap sizing respect the container, not the host.
      `-XX:+UseContainerSupport` is on by default. `[FLAG]` `[VERSION-TRAP]` `[RESEARCH]`
2.4.2 Verify it rather than assume it: `java -XX:+PrintFlagsFinal -version | grep MaxHeapSize`,
      and `-Xlog:os+container=trace` to see what the JVM read from cgroupfs. `[DUMP]` `[FLAG]`
2.4.3 Default `MaxRAMPercentage` is **25%** — deliberately conservative and almost always wrong for
      a dedicated service container. `[NUM]` `[TRAP]`
2.4.4 The replacement: `-XX:InitialRAMPercentage=60 -XX:MaxRAMPercentage=70`, leaving 25–35%
      headroom for metaspace, code cache, thread stacks, direct buffers, GC structures and malloc
      arenas. Show the arithmetic for a 2 GB and a 512 MB limit. `[FLAG]` `[NUM]` `[PROVE]`
2.4.5 `-Xmx` versus `-XX:MaxRAMPercentage`: the absolute flag is right when the limit is fixed and
      known; the percentage is right when the same image runs at several sizes. Never set both.
      `[TRAP]`
2.4.6 **Fractional CPU limits**: a `0.5` CPU limit still reports `availableProcessors() == 1`, and a
      `1.5` limit reports 1 (ceil of quota/period in older JDKs, and the rounding rule changed —
      verify). GC threads, ForkJoin common pool and Netty pools all size from this number.
      `-XX:ActiveProcessorCount=N` is the override. `[FLAG]` `[TRAP]` `[NUM]` `[RESEARCH]`
2.4.7 CPU **throttling** versus CPU **count**: a container with `limits.cpu: 2` but a 100 ms CFS
      period can be throttled mid-GC-pause, turning a 10 ms pause into 200 ms. Read
      `/sys/fs/cgroup/cpu.stat` `nr_throttled` / `throttled_usec`. `[X-REF 11]` `[X-REF 19]`
      `[PROVE]`
2.4.8 `requests` versus `limits` in Kubernetes and why memory limit == request for a JVM (no
      overcommit tolerance), while CPU limit is often best left unset. `[X-REF 19]` `[PROVE]`
2.4.9 The **container sizing worksheet**: start from the memory limit, subtract non-heap terms one
      by one with justification, and arrive at `-Xmx`. Do it for a 1 GB and a 4 GB container.
      `[NUM]` `[PROVE]`
2.4.10 Collector choice by container size: ≤1 CPU / ≤512 MB → Serial; 2 CPU / 1–4 GB → G1 (or
       Parallel for batch); ≥4 CPU with a pause SLO → ZGC. `[PROVE]`
2.4.11 Thread-count discipline in a small container: a default Tomcat pool of 200 threads at 1 MB of
       stack each is 200 MB of native memory nobody budgeted for. `[NUM]` `[TRAP]` `[X-REF 07]`
2.4.12 `-XX:NativeMemoryTracking=summary` as a permanent production setting (≈5–10% memory overhead,
       small CPU cost) versus `detail` for a debugging session. `[FLAG]` `[NUM]` `[RESEARCH]`
2.4.13 Diagnosing exit 137: check NMT-committed vs the limit, thread count × `-Xss`, metaspace
       growth, direct-buffer usage, and finally the RSS/NMT gap (glibc arenas, mapped files).
       `[PROVE]` `[DUMP]`
2.4.14 `MALLOC_ARENA_MAX=2` and `jcmd System.trim_native_heap` as the two cheap mitigations for the
       RSS/NMT gap. `[RESEARCH]` `[NUM]`
2.4.15 Base image choice: a JRE-less distroless image has no `jcmd`, no `jstack`, no `jfr` — you
       cannot diagnose what you cannot attach to. Either ship the tools or ship a debug sidecar with
       `shareProcessNamespace: true`. `[TRAP]` `[X-REF 19]`
2.4.16 Readiness versus liveness probes for a JVM: readiness must not pass until warmup is
       reasonable, and liveness must not kill a JVM that is merely in a long GC pause (set
       `timeoutSeconds` above your max pause). `[TRAP]` `[X-REF 19]` `[X-REF 20]`
2.4.17 Heap dumps in a container: the dump is heap-sized, `/tmp` is usually the container's writable
       layer and may be tiny, and the pod may be killed before you retrieve it. Mount a volume for
       `HeapDumpPath`. `[TRAP]` `[X-REF 19]`
2.4.18 `-XX:+UseSerialGC` plus `-XX:TieredStopAtLevel=1` plus AppCDS as the "small container, fast
       start, low footprint" combination, and when that is genuinely the right JVM. `[FLAG]`
       `[PROVE]`

*(18 leaves)*

## §2.5 Allocation economics and the object lifecycle

2.5.1 The full life of an object, stage by stage: `new` bytecode → TLAB pointer bump → constructor →
      publication → young GC survival and copy to survivor → age increment → promotion → old-gen
      residence → unreachable → marked dead → space reclaimed (possibly with a copy). Every stage
      has a cost you can name. `[PROVE]` `[RESEARCH]`
2.5.2 Why allocating many short-lived objects is genuinely cheap in Java, stated as a proof:
      pointer-bump allocation plus copying collection means the total cost is proportional to
      *survivors*, and short-lived objects are not survivors. `[PROVE]` `[NUM]`
2.5.3 The corollary that people get backwards: object *pooling* usually makes things worse, because
      it converts cheap young garbage into expensive old-gen live data and adds
      remembered-set/write-barrier pressure. Pool only what is expensive to construct (threads,
      connections, large direct buffers). `[TRAP]` `[PROVE]`
2.5.4 TLAB sizing and waste: `-XX:TLABSize`, `-XX:+ResizeTLAB` (on),
      `-XX:TLABWasteTargetPercent` (default 1), `-XX:MinTLABSize`. An object larger than the
      refill-waste threshold goes to the shared heap instead of retiring the TLAB. `[FLAG]`
      `[NUM]` `[RESEARCH]`
2.5.5 Measuring allocation without a profiler: `-Xlog:gc+tlab=trace`,
      `ThreadMXBean.getThreadAllocatedBytes`, JFR `jdk.ObjectAllocationSample`, and async-profiler
      `-e alloc`. `[DUMP]`
2.5.6 The allocation hot spots that actually appear in real services: autoboxing in a hot loop,
      `String` concatenation in logging, `Optional` in tight code, lambda capture creating a new
      object per call, iterator allocation, `stream()` on a small collection, defensive copies,
      `ByteBuffer.allocate` per request, and Jackson's per-call buffers. `[X-REF 02]` `[X-REF 04]`
2.5.7 Which of those the JIT eliminates for free via escape analysis (non-capturing lambdas,
      iterators over a local collection, small `Optional` chains) and which it cannot (anything
      stored, returned, or passed to a non-inlined method). This is the honest version of "don't
      micro-optimise". `[PROVE]` `[TRAP]`
2.5.8 The **card-marking write barrier** cost on every reference store to the heap, and why an
      old→young reference is more expensive than a young→young one. `[PROVE]` `[ASM]`
2.5.9 Large-object behaviour: humongous in G1, `-XX:PretenureSizeThreshold` in Parallel, and the
      "big array churn" anti-pattern that fills old gen with no leak. `[FLAG]` `[TRAP]`
2.5.10 Off-heap as an allocation strategy: direct buffers, memory-mapped files, `Arena`/
       `MemorySegment` (Java 22 FFM), Chronicle-style off-heap maps. What you gain (GC does not
       trace it) and what you pay (manual lifetime, no bounds safety from the collector, harder
       diagnostics). `[PROVE]`
2.5.11 The measurement discipline: allocation profiling (who allocates) is a different question from
       heap profiling (what is retained), and using the wrong one wastes a day. `[TRAP]`
       `[PROVE]`
2.5.12 A worked "reduce allocation rate by 10×" case: identify with `-e alloc`, fix the top three
       sites, re-measure GC frequency and p99. `[NUM]` `[PROVE]`

*(12 leaves)*

## §2.6 Class loading in practice

2.6.1 Startup class-loading budget: count classes with `-Xlog:class+load` and measure the time in
      `-Xlog:class+load=info` timestamps or JFR `jdk.ClassLoad`. `[NUM]` `[DUMP]`
2.6.2 What Spring Boot does at startup and why it loads so many classes: component scanning,
      auto-configuration `@Conditional` evaluation, proxy generation, and Jackson/Hibernate
      metadata. `[X-REF 07]`
2.6.3 Spring's AOT processing (`spring-boot-maven-plugin process-aot`) and how it moves
      configuration work to build time, complementing CDS/AOT-cache. `[X-REF 07]` `[RESEARCH]`
2.6.4 Diagnosing "which jar did this class come from": `-Xlog:class+load=info`,
      `getClass().getProtectionDomain().getCodeSource().getLocation()`, and `jdeps`. `[DUMP]`
2.6.5 Duplicate-class and version-conflict diagnosis: `mvn dependency:tree`, `gradle
      dependencyInsight`, the Maven enforcer `banDuplicateClasses` rule, and shading as the last
      resort. `[X-REF 07]`
2.6.6 The `NoSuchMethodError` at runtime with a green build: the classic split-version problem, and
      why compile-time and runtime classpaths differing is the root cause. `[TRAP]` `[X-REF 03]`
2.6.7 Agents: `-javaagent:` (premain), dynamic attach (`agentmain` via
      `VirtualMachine.attach(pid).loadAgent(...)`), and `-agentpath:` for native agents. `[FLAG]`
2.6.8 What an agent costs: every loaded class passes through every `ClassFileTransformer`, adding
      startup time and metaspace, and instrumented methods may become too large to inline.
      APM agents commonly add 5–20% startup and measurable throughput cost. `[NUM]` `[TRAP]`
      `[RESEARCH]`
2.6.9 `Instrumentation` API surface: `addTransformer`, `retransformClasses`, `redefineClasses`,
      `getObjectSize`, `appendToBootstrapClassLoaderSearch`, `isModifiableClass`. `[RESEARCH]`
2.6.10 Redefinition limits: HotSwap can change method bodies only — not add/remove methods or
       fields, not change the hierarchy. Everything beyond that needs a restart or DCEVM.
       `[TRAP]`
2.6.11 Dynamic attach hardening: `-XX:+DisableAttachMechanism` breaks every diagnostic tool, and
       `-Djdk.attach.allowAttachSelf=false` is the default since Java 9 (so self-attach for
       profilers needs an explicit opt-in). `[FLAG]` `[TRAP]` `[RESEARCH]`
2.6.12 Reflection's cost model: `Method.invoke` was a generated accessor + boxing before Java 18;
       JEP 416 reimplemented core reflection on method handles, closing most of the gap. `setAccessible`
       is still an access check. `[VERSION-TRAP]` `[X-REF 03]` `[RESEARCH]`
2.6.13 The classloader-leak *prevention* checklist: deregister JDBC drivers, cancel timers, shut down
       executors, remove `ThreadLocal`s, deregister MBeans and shutdown hooks, clear
       `java.beans.Introspector` caches, and never cache a `Class` from an app loader in a static
       field of a JDK class. `[TRAP]` `[X-REF 05]`
2.6.14 Detecting a leak *before* production: redeploy N times in a test environment and assert on
       loaded-classloader count via `jcmd VM.classloaders`. `[PROVE]`
2.6.15 The metaspace sizing rule for a redeploy-heavy environment: cap it, alarm on it, and treat
       growth across redeploys as a bug rather than a tuning problem. `[PROVE]`

*(15 leaves)*

## §2.7 JIT in practice, and benchmarking

2.7.1 What warmup actually costs, measured: time-to-first-request, time-to-steady-state throughput,
      and the number of requests to reach 95% of peak. Report all three, not "it's slow at first".
      `[NUM]` `[PROVE]`
2.7.2 The deployment consequences: ramp traffic in a canary rather than switching it; make the
      readiness probe wait; consider a synthetic warmup request loop at startup; and be aware that
      autoscaling *adds* cold JVMs precisely when load is highest. `[PROVE]` `[X-REF 19]`
2.7.3 Why a warmup loop must exercise the *same* code paths and receiver types: warming with one
      implementation and serving with three turns a monomorphic call site megamorphic and
      deoptimises. `[TRAP]` `[PROVE]`
2.7.4 **JMH** and why naive benchmarks are worthless: no warmup measures the interpreter, dead-code
      elimination deletes your computation, constant folding evaluates it at compile time, loop
      unrolling changes the shape, and one fork shares a JIT profile between variants. `[TRAP]`
      `[PROVE]`
2.7.5 The JMH surface: `@Benchmark`, `@BenchmarkMode` (Throughput, AverageTime, SampleTime,
      SingleShotTime, All), `@OutputTimeUnit`, `@Warmup`, `@Measurement`, `@Fork`, `@State`
      (Benchmark, Group, Thread), `@Setup`/`@TearDown` (Trial, Iteration, Invocation), `@Param`,
      `@Threads`, `@Group`/`@GroupThreads`, `Blackhole`, `@CompilerControl`. `[BUILD]`
      `[RESEARCH]`
2.7.6 Returning a value from `@Benchmark` or consuming it with a `Blackhole` — and what a compiler
      blackhole actually does (JMH 1.34+ uses a JVM-supported blackhole intrinsic rather than the
      old volatile-store trick). `[PROVE]` `[RESEARCH]`
2.7.7 `-prof gc`, `-prof perfasm`, `-prof jfr`, `-prof async` as the JMH profilers that turn a
      number into an explanation. `[RESEARCH]`
2.7.8 What JMH cannot tell you: anything about your real workload's mix, cache behaviour under
      concurrent load, or GC behaviour at production heap sizes. Microbenchmarks answer
      microquestions. `[TRAP]` `[PROVE]`
2.7.9 Diagnosing "it got slower after a deploy" as a JIT problem: check `jdk.Compilation` and
      `jdk.Deoptimization` in JFR, check `Compiler.codecache` for exhaustion, check whether an
      agent was added, and check whether a new subclass made a hot call site megamorphic. `[PROVE]`
      `[DUMP]`
2.7.10 `-XX:+PrintCompilation` in production is too noisy; `-XX:+LogCompilation` plus JITWatch is the
       offline tool. `[RESEARCH]`
2.7.11 Writing JIT-friendly code, with the honest caveat that this list is short and most of it is
       just good code: small methods, stable types at hot call sites, `final` where it is true,
       avoid megamorphic dispatch in the innermost loop, avoid exceptions for control flow, avoid
       reflection in hot paths. `[PROVE]`
2.7.12 **Trap:** "`final` on a method helps the JIT." It does not — HotSpot devirtualises from the
       *observed* class hierarchy, so a non-final method with one implementation is inlined just as
       well, and `final` is a design statement, not an optimisation. `[TRAP]` `[PROVE]`
       `[X-REF 03]`
2.7.13 **Trap:** "the JIT compiles the whole program eventually." It compiles what is hot; cold code
       stays interpreted forever, which is fine and is the design. `[TRAP]`
2.7.14 The interaction with the AOT cache (JEP 515 method profiles): warmup is no longer purely a
       runtime phenomenon in Java 25+, which changes this section's advice for new deployments.
       `[VERSION-TRAP]` `[RESEARCH]`

*(14 leaves)*

## §2.8 Startup and warmup engineering

2.8.1 Decompose startup before optimising it: JVM init, class loading and verification, static
      initialisers, framework bootstrap (Spring context), connection-pool warmup, and JIT warmup.
      Measure each. `[PROVE]` `[NUM]`
2.8.2 Measuring: `-Xlog:startuptime` (where available), Spring Boot's own startup log,
      `ApplicationStartup`/`BufferingApplicationStartup`, JFR from time zero, and simply timestamping
      `main`. `[X-REF 07]` `[DUMP]`
2.8.3 CDS: create with `-XX:ArchiveClassesAtExit=app.jsa`, use with `-XX:SharedArchiveFile=app.jsa`,
      verify with `-Xlog:class+load=info` showing `shared objects file`. `[FLAG]` `[DUMP]`
2.8.4 The CDS caveats: the archive is tied to the exact JDK build and classpath *string*, it is
      invalidated silently (`-Xshare:auto` just falls back), and `-Xshare:on` makes the failure
      loud. Always use `on` in CI to prove the archive is being used. `[TRAP]` `[FLAG]`
2.8.5 Spring Boot 3.3+ `CDS` support and the buildpack integration (`-Dspring.aot.enabled=true`
      plus a training run) as the productionised version of the above. `[X-REF 07]` `[RESEARCH]`
2.8.6 The AOT cache workflow in Java 24 (two-step: `-XX:AOTMode=record` →
      `-XX:AOTMode=create` → `-XX:AOTCache=app.aot`) and the Java 25 one-step
      `-XX:AOTCacheOutput=app.aot`. `[FLAG]` `[VERSION-TRAP]` `[RESEARCH]`
2.8.7 The training-run problem common to CDS, AOT and PGO: the recorded profile must resemble
      production, and a training run that only starts the app captures startup, not steady state.
      `[TRAP]` `[PROVE]`
2.8.8 GraalVM native image in practice: `native-image` build, the reachability metadata repository,
      `@RegisterReflectionForBinding`, `--initialize-at-build-time` versus `--initialize-at-run-time`
      and the class-initialisation traps it creates, and the build-time/memory cost. `[TRAP]`
      `[RESEARCH]`
2.8.9 What breaks under native image: dynamic proxies without config, `Class.forName` on a computed
      name, service loading without metadata, JMX, most agents, and anything that generates
      bytecode at runtime (which includes some Spring/Hibernate paths without AOT). `[TRAP]`
      `[RESEARCH]`
2.8.10 Diagnostics under native image: no `jcmd`/`jstack` in the classic sense, but JFR is supported
       (`-XX:+FlightRecorder` at build), plus heap dumps in GraalVM Enterprise. Know the reduced
       toolbox before you commit. `[TRAP]` `[RESEARCH]`
2.8.11 The **decision framework**: request rate and lifetime → if the process lives for hours and is
       CPU-bound, HotSpot + AOT cache wins; if it lives for seconds (serverless/CLI), native image
       or CRaC wins; if you need full dynamic behaviour and diagnostics, stay on HotSpot. `[PROVE]`
       `[RESEARCH]`
2.8.12 A measured comparison table to reproduce: startup, time-to-peak, peak throughput, RSS, build
       time, and diagnostic support, for plain JVM / AppCDS / AOT cache / native image on the same
       Spring Boot service. `[NUM]` `[RESEARCH]`

*(12 leaves)*

## §2.9 Heap dumps and leak hunting

2.9.1 The **leak workflow**, end to end and in order: (1) `jstat -gcutil <pid> 1s 60` and watch the
      **old-gen floor after each full GC** — monotonic rise = leak, stable = undersized or spiky;
      (2) `jmap -histo:live` at two points and diff — which class grew; (3) take a heap dump;
      (4) MAT Leak Suspects and Dominator Tree; (5) Path to GC Roots excluding weak/soft. `[PROVE]`
      `[DUMP]`
2.9.2 **Retained size** (what would be freed if this object were collected) versus **shallow size**
      (the object itself). Only retained size identifies a culprit. `[TRAP]` `[PROVE]`
2.9.3 The **dominator tree**: X dominates Y if every path from a root to Y goes through X. This is
      why the dominator tree, not the reference graph, is the leak-finding view. `[PROVE]`
2.9.4 Taking the dump: `jcmd <pid> GC.heap_dump /path/heap.hprof`, `jmap -dump:live,format=b`, or
      `-XX:+HeapDumpOnOutOfMemoryError`. `live` forces a full GC first (smaller, cleaner dump);
      omitting it captures unreachable objects too (useful for allocation questions). `[TRAP]`
2.9.5 The costs: the JVM is paused for the dump, the file is roughly live-heap-sized, and writing
      8 GB to a slow volume takes minutes. Plan for it. `[NUM]` `[TRAP]`
2.9.6 `-XX:+HeapDumpBeforeFullGC` / `-XX:+HeapDumpAfterFullGC` and
      `-XX:HeapDumpGzipLevel` (Java 17+) for large heaps. `[FLAG]` `[RESEARCH]`
2.9.7 Analysing a dump larger than your laptop: run MAT headless
      (`ParseHeapDump.sh` with `-Xmx`), or use `jhat`'s successors / `heaphero` / `jvisualvm`
      with an index. `[RESEARCH]`
2.9.8 MAT specifics worth naming: `Histogram`, `Dominator Tree`, `Top Consumers`, `Duplicate
      Classes` (a classloader-leak detector), `Merge Shortest Paths to GC Roots`,
      `Immediate Dominators`, `OQL`, and the `unreachable objects histogram`. `[RESEARCH]`
2.9.9 **The Spring/Java leak culprit list**, each with its signature in a dump: an unbounded
      `HashMap`/`ConcurrentHashMap` cache in a singleton bean (the single most common one);
      `ThreadLocal` values never removed on pooled request threads; listeners/callbacks/
      `@EventListener` objects never deregistered; `static` collections accumulating; non-static
      inner classes and anonymous listeners pinning their enclosing object; unclosed JDBC
      connections/streams/`HttpClient` responses exhausting a pool; request- or session-scoped state
      accidentally promoted to singleton scope; interned or `substring`-derived strings retained in
      a long-lived structure; an unbounded `LinkedBlockingQueue` in a thread pool backing up under
      load; a `WeakHashMap` whose values reference their keys; and a growing `ClassLoader` count
      from redeploys. `[TRAP]` `[X-REF 05]` `[X-REF 07]`
2.9.10 The fix that generalises: **bound everything**. Caffeine with `maximumSize` +
       `expireAfterWrite` instead of a raw map; bounded queues; bounded pools; bounded retry
       buffers. `[X-REF 15]` `[PROVE]`
2.9.11 JFR's `jdk.OldObjectSample` as a **leak profiler without a heap dump**: it samples surviving
       allocations and records their allocation stack, giving you *where the object was created*,
       which a heap dump cannot. Enable with `settings=profile` or
       `-XX:StartFlightRecording=...,+jdk.OldObjectSample#enabled=true`. `[RESEARCH]` `[PROVE]`
2.9.12 A **native** leak has none of these signatures: heap flat, NMT-committed rising or RSS rising
       above NMT. Route to §2.12 instead of taking another heap dump. `[TRAP]` `[PROVE]`
2.9.13 Distinguishing a leak from a cache from a legitimate large live set: ask what the *bound* is.
       If nobody can state one, it is a leak waiting for enough traffic. `[PROVE]`
2.9.14 Preventing regressions: assert on heap floor in a soak test, alarm on
       `jvm_memory_used_bytes{area="heap"}` post-GC floor, and treat metaspace growth across
       redeploys as a failing test. `[X-REF 20]` `[X-REF 16]`

*(14 leaves)*

## §2.10 Thread dumps and CPU workflows

2.10.1 **The 100%-CPU workflow**, as a procedure: (1) `top -H -p <pid>` to find the *thread* burning
       CPU and note its decimal TID; (2) `printf '%x\n' <tid>` because dumps print `nid` in hex;
       (3) `jstack <pid> > dump.txt`, **three times a few seconds apart**; (4) grep
       `nid=0x<hex>` and read the stack. A thread stuck at the same frame across all three is the
       culprit; a moving stack is just busy work. `[PROVE]` `[DUMP]` `[X-REF 11]`
2.10.2 The findings you should expect and their fixes: an infinite loop, catastrophic regex
       backtracking, a degenerate hash bucket, an unbounded retry loop, JSON serialisation of a huge
       object — and, very commonly, **GC**, where the hot threads are `GC task thread#N` and the
       real problem is heap pressure. Check `jstat -gcutil` *before* blaming application code.
       `[TRAP]` `[X-REF 02]`
2.10.3 Compiler threads (`C2 CompilerThread0`) burning CPU means a deopt storm or a huge method, not
       an application bug. `[TRAP]`
2.10.4 Reading a thread dump's anatomy: the header, `"name" #id daemon prio os_prio tid nid state`,
       the `java.lang.Thread.State` line, the stack, the `- locked <0x...>` /
       `- waiting to lock <0x...>` / `- parking to wait for <0x...>` annotations, the JNI global
       reference count, and the deadlock section. `[DUMP]` `[X-REF 05]`
2.10.5 Dump *patterns* and what each means: many BLOCKED on one monitor (contention — find the
       owner), many WAITING on a pool queue (idle, normal), many RUNNABLE in socket reads (waiting on
       a downstream, and the JVM cannot tell), many TIMED_WAITING in `Unsafe.park` (a pool with no
       work), all threads in the same downstream call (a saturated dependency). `[PROVE]`
       `[X-REF 05]`
2.10.6 `jstack` prints "Found one Java-level deadlock" explicitly for monitor and `ReentrantLock`
       cycles — and finds **nothing** for a class-initialisation deadlock, a database deadlock, a
       semaphore starvation cycle, or a thread-pool dependency deadlock. `[TRAP]` `[X-REF 05]`
2.10.7 Taking a dump is a **safepoint operation**, so a dump on a 4000-thread JVM is itself a pause.
       `[TRAP]` `[NUM]`
2.10.8 Virtual threads change the workflow: `jstack` shows only carriers.
       `jcmd Thread.dump_to_file -format=json` is the replacement, and the "idle JVM with no work
       happening" signature of all-carriers-pinned is the trap. `[X-REF 05]` `[VERSION-TRAP]`
2.10.9 CPU attribution without a dump: async-profiler `-e cpu` for a flame graph, `-e wall` for
       "why is it slow when the CPU is idle", `-e lock` for contention, `-e alloc` for allocation.
       Choosing the event is the skill. `[PROVE]` `[RESEARCH]`
2.10.10 `perf top -p <pid>` plus `perf-map-agent`/async-profiler's `-e itimer` for mixed
        Java/native profiles, and reading `[unknown]` frames as a symbol problem, not a mystery.
        `[X-REF 11]` `[RESEARCH]`
2.10.11 Correlating a dump with metrics: a thread dump alone tells you the *state*, not the *trend*.
        Always pair with GC stats, CPU, and request-rate graphs. `[X-REF 20]`
2.10.12 High system CPU (`sy` in `top`) versus user CPU: system time points at syscalls, page
        faults, or context-switch storms, not at your algorithm. `[X-REF 11]` `[TRAP]`
2.10.13 The "slow but not busy" case: low CPU, high latency → blocked on I/O, lock contention,
        connection-pool exhaustion, or GC. Wall-clock profiling and the connection-pool metrics are
        the tools, not a CPU flame graph. `[PROVE]` `[X-REF 20]`

*(13 leaves)*

## §2.11 JFR in production

2.11.1 The case for always-on JFR: <1% overhead at `default`, a circular buffer you can dump *after*
       the incident, and event coverage across GC, allocation, locks, I/O, exceptions, compilation
       and safepoints in one artifact. `[NUM]` `[PROVE]`
2.11.2 Configuration: `-XX:StartFlightRecording=name=prod,maxsize=256m,maxage=6h,settings=default,
       dumponexit=true,filename=/var/dumps/exit.jfr`. Each parameter defended. `[FLAG]`
2.11.3 `default` versus `profile` settings templates: sampling rates, allocation-event throttling
       (150/s vs 300/s), and the extra events `profile` enables. Custom `.jfc` files via
       `jfr configure`. `[NUM]` `[RESEARCH]`
2.11.4 Dumping on demand: `jcmd <pid> JFR.dump name=prod filename=/tmp/now.jfr`, and
       `JFR.check` to see what is running. `[DUMP]`
2.11.5 **Event streaming** (JEP 349, Java 14): `RecordingStream` consuming events in-process or
       out-of-process, which turns JFR into a metrics source rather than a post-mortem artifact.
       `[BUILD]` `[RESEARCH]`
2.11.6 The questions JFR answers better than anything else: which allocation sites dominate, which
       exceptions are thrown at volume and silently caught, which methods dominate CPU, what the
       real safepoint pause distribution is, and which sockets/files are slow. `[PROVE]`
2.11.7 `jdk.ExceptionStatistics` and the "10 000 exceptions/second being swallowed" finding that no
       other tool surfaces. `[PROVE]` `[TRAP]`
2.11.8 The limits: sampling means rare events are missed, `ObjectAllocationSample` is throttled so
       counts are estimates, and JFR cannot see native allocations before Java 24's
       `jdk.NativeMemoryUsage`. `[TRAP]` `[RESEARCH]`
2.11.9 Reading a recording without JMC: `jfr summary r.jfr`,
       `jfr print --events jdk.GarbageCollection r.jfr`, `jfr print --json`. `[DUMP]`
2.11.10 JMC's automated analysis rules as a triage shortcut, and the honest caveat that they produce
        false positives you must be able to overrule. `[TRAP]`
2.11.11 Custom events for domain-level tracing (a `QuizSubmissionEvent` with the quiz id and
        latency), and why that beats a log line for post-incident analysis. `[BUILD]`
        `[X-REF 20]`
2.11.12 JFR versus Micrometer/Prometheus versus distributed tracing: aggregate metrics tell you
        *that*, JFR tells you *where in the JVM*, traces tell you *where in the system*. Use all
        three, know which question each answers. `[X-REF 20]` `[PROVE]`

*(12 leaves)*

## §2.12 Native memory and the RSS gap

2.12.1 The diagnosis order for "RSS keeps growing but the heap is fine": (1) NMT summary and diff,
       (2) thread count × `-Xss`, (3) metaspace and code cache, (4) direct + mapped buffers,
       (5) the NMT-to-RSS gap. `[PROVE]`
2.12.2 `-XX:NativeMemoryTracking=summary|detail`, then `jcmd VM.native_memory summary scale=MB`,
       `baseline`, and `summary.diff` — the diff is the tool, not the snapshot. `[DUMP]`
2.12.3 Reading an NMT report: per-category `reserved` and `committed`, the `Total` line, and the
       `Thread` category's `(stack: reserved=... committed=...)` breakdown. `[DUMP]` `[NUM]`
2.12.4 NMT's blind spots, stated exactly: it does **not** track third-party native libraries, JNI
       `malloc` by user code, or the JDK's own class-library native allocations in all cases. This is
       why NMT-committed can be far below RSS. `[TRAP]` `[RESEARCH]`
2.12.5 The other components of the gap: glibc per-arena free lists and tcache holding freed memory,
       mapped shared libraries and the JDK image, and page-cache-backed mapped files. Reported gaps
       of 500 MB+ are ordinary on a many-core machine. `[NUM]` `[RESEARCH]`
2.12.6 Native leak hunting proper: `jemalloc`/`tcmalloc` with profiling enabled,
       `MALLOC_CONF=prof:true`, `jeprof` flame graphs, `pmap -X <pid>` for the mapping list, and
       `/proc/<pid>/smaps_rollup` for the authoritative RSS breakdown. `[X-REF 11]` `[RESEARCH]`
2.12.7 The usual native culprits in a Java service: a JNI library leaking, Netty direct buffers,
       a compression/crypto library, `Inflater`/`Deflater` not `end()`ed,
       `ZipFile`/`JarFile` not closed, and an APM agent. `[TRAP]` `[RESEARCH]`
2.12.8 `Inflater`/`Deflater`/`ZipInputStream` as a specific, common, easily-missed native leak with a
       `Cleaner` safety net that only runs at GC time. `[TRAP]` `[PROVE]`
2.12.9 `jcmd System.native_heap_info` and `jcmd System.trim_native_heap` (Linux, Java 18+) as the
       two commands most people have never run. `[DUMP]` `[RESEARCH]`
2.12.10 `-XX:MaxDirectMemorySize` set explicitly (rather than defaulting to `-Xmx`) so that direct
        memory exhaustion produces a Java error rather than an OOMKill. `[FLAG]` `[PROVE]`
2.12.11 Monitoring direct memory: `BufferPoolMXBean` (`direct` and `mapped` pools) exposed through
        Micrometer as `jvm_buffer_memory_used_bytes`. Alarm on it. `[X-REF 20]`
2.12.12 The FFM API's `Arena` lifetimes (`global`, `auto`, `confined`, `shared`) as the modern,
        *deterministic* alternative to `Cleaner`-based native memory. `[X-REF §3.22]`
        `[RESEARCH]`
2.12.13 A worked case: 2 GB container, `-Xmx1g`, RSS 1.95 GB, heap 400 MB — walk the terms and find
        the 300 threads and the 400 MB of malloc arenas. `[NUM]` `[PROVE]`

*(13 leaves)*

## §2.13 The observability surface of the JVM itself

2.13.1 The MXBean inventory and what each exposes: `RuntimeMXBean` (uptime, input arguments),
       `MemoryMXBean` (heap/non-heap usage, `setVerbose`), `MemoryPoolMXBean` (per-pool usage,
       peak, collection usage, **usage threshold notifications**), `GarbageCollectorMXBean`
       (collection count and time per collector), `ThreadMXBean` (counts, CPU time, deadlock
       detection, allocated bytes), `ClassLoadingMXBean`, `CompilationMXBean`,
       `OperatingSystemMXBean` (process and system CPU load, container-aware since Java 14),
       `BufferPoolMXBean`, `HotSpotDiagnosticMXBean` (dump heap, get/set VM options).
       `[RESEARCH]` `[X-REF 20]`
2.13.2 `MemoryPoolMXBean.setCollectionUsageThreshold` as a built-in leak alarm: fire a notification
       when a pool is still above X% *after* a collection. Almost nobody uses it. `[BUILD]`
       `[PROVE]`
2.13.3 Micrometer's JVM binders and the metric names they produce: `jvm_memory_used_bytes`,
       `jvm_memory_committed_bytes`, `jvm_memory_max_bytes`, `jvm_gc_pause_seconds`,
       `jvm_gc_memory_promoted_bytes_total`, `jvm_gc_memory_allocated_bytes_total`,
       `jvm_threads_live_threads`, `jvm_threads_states_threads`, `jvm_classes_loaded_classes`,
       `jvm_buffer_memory_used_bytes`, `process_cpu_usage`, `system_cpu_usage`. `[X-REF 20]`
       `[RESEARCH]`
2.13.4 The four JVM alerts worth paging on: post-GC old-gen occupancy above X% sustained, GC CPU
       share above 5–10%, metaspace above X% of max, and thread count trending up. Everything else
       is a dashboard. `[X-REF 20]` `[PROVE]`
2.13.5 JMX remote in production: `-Dcom.sun.management.jmxremote.*`, the RMI two-port problem
       behind NAT/Kubernetes, and why `jcmd` over `kubectl exec` is usually the better answer.
       `[TRAP]` `[X-REF 19]`
2.13.6 `jvm.options`/`JAVA_TOOL_OPTIONS` sprawl as an operational hazard: log the effective flags at
       startup (`-XX:+PrintFlagsFinal` filtered, or `RuntimeMXBean.getInputArguments()`) so an
       incident review can see what the JVM actually ran with. `[PROVE]`
2.13.7 Correlating JVM signals with request-level SLOs: a GC pause histogram overlaid on the p99
       latency graph is the single most persuasive incident artifact you can produce.
       `[X-REF 20]`
2.13.8 What to capture *automatically* on OOM or crash so the post-mortem is possible: heap dump,
       JFR dump on exit, `hs_err` file, GC log, and the last thread dump. All five, to a mounted
       volume. `[PROVE]` `[X-REF 19]`

*(8 leaves)*

## §2.14 Choosing a runtime

2.14.1 The distribution landscape and what actually differs: Oracle JDK (licence, no Shenandoah),
       Eclipse Temurin, Amazon Corretto, Azul Zulu/Prime (C4 pauseless GC), Red Hat build
       (Shenandoah), Microsoft build, GraalVM (JIT + native image), IBM Semeru/OpenJ9 (different VM
       entirely). `[RESEARCH]`
2.14.2 OpenJ9 as the genuinely different implementation: different GC policies (`gencon`,
       `balanced`, `metronome`), a different JIT (Testarossa), shared class cache, and much lower
       idle footprint — with different flags for everything in this guide. `[TRAP]` `[RESEARCH]`
2.14.3 LTS cadence and what "supported" means: 8, 11, 17, 21, 25, with a new LTS every two years
       since 21. Version choice is a JVM-internals decision because collectors and headers change
       across it. `[NUM]` `[RESEARCH]`
2.14.4 The upgrade argument in JVM-internals terms: 8 → 17 buys G1 by default plus a modern G1,
       compact strings and a parallel full GC; 17 → 21 buys generational ZGC and virtual threads;
       21 → 25 buys compact headers and the AOT cache. `[VERSION-TRAP]` `[PROVE]`
2.14.5 The migration hazards, in order of how often they bite: removed GC flags failing startup,
       `URLClassLoader` casts, illegal reflective access, `javax` → `jakarta`, removed
       `sun.misc.Unsafe` methods, and agents built against an older class file version. `[TRAP]`
       `[X-REF 03]`
2.14.6 HotSpot versus GraalVM JIT versus native image versus OpenJ9 as a four-way table on startup,
       warmup, peak, footprint, tooling, and operational familiarity. `[NUM]`
2.14.7 The honest default: HotSpot LTS with G1, tuned by measurement, is right for the large
       majority of backend services, and every alternative needs a specific reason. `[PROVE]`

*(7 leaves)*

## §2.15 Version delta, JDK 8 → 25

2.15.1 **Java 8**: PermGen removed for metaspace (JEP 122), G1 present but not default, tiered
       compilation on by default, `-XX:+UseStringDeduplication` arrives in 8u20, container support
       backported in 8u191. `[VERSION-TRAP]`
2.15.2 **Java 9**: G1 becomes the **default collector**; unified logging (`-Xlog`, JEP 158/271)
       replaces the old print flags; segmented code cache (JEP 197); compact strings (JEP 254);
       the module system changes the loader hierarchy and removes `rt.jar`; CMS deprecated (JEP
       291); `Cleaner` added; `VarHandle` (JEP 193). `[VERSION-TRAP]`
2.15.3 **Java 10**: container awareness by default (JEP opt via `UseContainerSupport`);
       **thread-local handshakes** (JEP 312); parallel full GC for G1 (JEP 307); Application CDS
       (JEP 310); `-XX:AllocateHeapAt` for alternative memory devices (JEP 316).
       `[VERSION-TRAP]`
2.15.4 **Java 11**: **ZGC** (experimental, JEP 333), **Epsilon** (JEP 318), **JFR open-sourced**
       (JEP 328), `-XX:+UseAppCDS` folded in, low-overhead heap profiling (JEP 331), removal of the
       standalone JRE. `[VERSION-TRAP]`
2.15.5 **Java 12**: **Shenandoah** (experimental, JEP 189), G1 abortable mixed collections (JEP 344),
       G1 promptly returns unused memory (JEP 346), default CDS archive (JEP 341).
       `[VERSION-TRAP]`
2.15.6 **Java 13**: **dynamic CDS archives** (JEP 350), ZGC uncommits memory (JEP 351).
       `[VERSION-TRAP]`
2.15.7 **Java 14**: **CMS removed** (JEP 363), Parallel GC deprecated combos removed, ZGC on macOS
       and Windows, **JFR event streaming** (JEP 349), helpful NullPointerExceptions (JEP 358),
       `-XX:+ShowCodeDetailsInExceptionMessages`. `[VERSION-TRAP]`
2.15.8 **Java 15**: **ZGC and Shenandoah become production** (JEP 377, 379), **biased locking
       disabled and deprecated** (JEP 374), hidden classes (JEP 371). `[VERSION-TRAP]`
2.15.9 **Java 16**: **Elastic Metaspace** (JEP 387), ZGC concurrent thread-stack processing (JEP
       376), strong encapsulation by default (JEP 396), `jdk.ObjectAllocationSample` improvements.
       `[VERSION-TRAP]`
2.15.10 **Java 17 (LTS)**: `--illegal-access` removed (JEP 403), always-strict floating point (JEP
        306), macOS/AArch64 port (JEP 391), deprecation of the Security Manager (JEP 411), G1 and
        ZGC maturity work. `[VERSION-TRAP]`
2.15.11 **Java 18**: `-Xverify:none` becomes a no-op, **finalization deprecated for removal / can be
        disabled** (JEP 421), UTF-8 by default (JEP 400), biased locking **removed**, string
        deduplication for all collectors (JEP 192 generalisation). `[VERSION-TRAP]` `[RESEARCH]`
2.15.12 **Java 19/20**: virtual threads preview (JEP 425/436), structured concurrency incubator, ZGC
        and Shenandoah incremental improvements, FFM preview iterations. `[X-REF 05]`
        `[VERSION-TRAP]`
2.15.13 **Java 21 (LTS)**: **Generational ZGC** (JEP 439), **virtual threads final** (JEP 444),
        `jcmd Thread.dump_to_file -format=json`, sequenced collections, `-XX:+ZGenerational` as the
        opt-in. `[VERSION-TRAP]`
2.15.14 **Java 22/23**: FFM API final (JEP 454, Java 22), region pinning for G1 (JEP 423, Java 22 —
        removes the GC-locker JNI-critical pause), **generational ZGC becomes the default** and
        non-generational deprecated (JEP 474, Java 23), `sun.misc.Unsafe` memory access deprecated
        (JEP 471, Java 23), late barrier expansion for G1 (JEP 475, Java 24 draft in 23).
        `[VERSION-TRAP]` `[RESEARCH]`
2.15.15 **Java 24**: **compact object headers experimental** (JEP 450), **AOT class loading and
        linking** (JEP 483), **generational Shenandoah** (JEP 404), **non-generational ZGC removed**
        (JEP 490), **late G1 barrier expansion** (JEP 475), `sun.misc.Unsafe` memory-access warnings
        (JEP 498), JNI restricted by default (JEP 472), synchronized no longer pins virtual threads
        (JEP 491). `[VERSION-TRAP]` `[X-REF 05]` `[RESEARCH]`
2.15.16 **Java 25 (LTS)**: **compact object headers become a product feature** (JEP 519),
        **AOT command-line ergonomics** (JEP 514) and **AOT method profiling** (JEP 515),
        **generational Shenandoah productised**, scoped values final (JEP 506), and
        `jdk.NativeMemoryUsage`-style native-memory JFR events. `[VERSION-TRAP]` `[RESEARCH]`
2.15.17 The three "your notes are stale" checks to run before any interview: is CMS still in your
        answer (removed in 14), is biased locking still in your answer (removed in 18), and is ZGC
        still described as non-generational (default generational since 23). `[VERSION-TRAP]`
        `[TRAP]`

*(17 leaves)*

---

**PART 2 total: 8+16+16+18+12+15+14+12+14+13+12+13+8+7+17 = 195 leaves**

---

# PART 3 — UNDER THE HOOD

Every `[SOURCE]` leaf here must quote real HotSpot source, JVMS text or JEP text — a short excerpt,
then every line explained. Every constant must be named with its value and the file it lives in.

## §3.1 The HotSpot runtime skeleton

3.1.1 The three subsystems of HotSpot as the OpenJDK docs name them: the **runtime** (class loading,
      linking, threads, monitors, exceptions, JNI, VM operations), the **compilers** (interpreter,
      C1, C2), and the **memory manager** (GC). Every later section is one of these. `[SOURCE]`
      `[RESEARCH]`
3.1.2 The source-tree map so you can go read it: `src/hotspot/share/{oops,classfile,interpreter,
      runtime,opto,c1,gc,jfr,prims,code,memory,utilities}` and what each contains. `[SOURCE]`
3.1.3 `globals.hpp` and the flag declaration macros (`product`, `develop`, `diagnostic`,
      `experimental`) as the single authoritative list of every `-XX:` flag and its default.
      **This is how you verify a constant rather than trusting a blog.** `[SOURCE]` `[PROVE]`
3.1.4 `JavaThread` versus `java.lang.Thread` versus the OS thread: three objects, one logical
      thread, and the `_anchor`/`last_Java_frame` that lets the VM find the Java stack from native
      code. `[SOURCE]` `[X-REF 05]`
3.1.5 `ThreadLocalStorage` and the current-thread lookup; why `Thread.currentThread()` is
      essentially free. `[PROVE]`
3.1.6 The `VMThread`, the `WatcherThread` (periodic tasks), the `Finalizer` thread, the
      `Reference Handler` thread, `Signal Dispatcher`, `Notification Thread`, the compiler threads,
      the GC threads, and `Common-Cleaner` — the JVM's own threads, all of which appear in your
      thread dump and none of which are your code. `[DUMP]` `[TRAP]`
3.1.7 `CodeBlob`, `nmethod` and `CodeCache` as the objects that hold compiled code, and the
      `nmethod` state machine (`in_use` → `not_entrant` → `zombie`/`unloaded`). `[SOURCE]`
3.1.8 Handles and `HandleMark`: why native VM code must not hold raw oops across a safepoint, and
      what a `Handle` is for. `[SOURCE]` `[PROVE]`
3.1.9 `Universe` and the well-known klasses; `SystemDictionary` as the (name, loader) → klass map
      that implements §1.4.7. `[SOURCE]`
3.1.10 The `Arena`/`ResourceArea` allocator the VM uses for its own scratch memory, and its
       appearance as the NMT `Arena Chunk` category. `[SOURCE]` `[RESEARCH]`

*(10 leaves)*

## §3.2 The template interpreter

3.2.1 HotSpot's interpreter is **generated at startup**: `TemplateTable` holds an assembly template
      per bytecode, and `TemplateInterpreterGenerator` emits a real machine-code interpreter into
      the code cache before `main` runs. `[SOURCE]` `[RESEARCH]`
3.2.2 Why generate rather than write a C `switch` loop: the generated code can keep the top of the
      operand stack in registers, use platform-specific instructions, and dispatch with a single
      indirect jump. It is roughly 2–3× a naive switch interpreter. `[PROVE]` `[NUM]`
3.2.3 The **dispatch table**: a jump table indexed by opcode *and* by the interpreter's current
      tos-state (top-of-stack cached type), so each bytecode has several entry points. `[SOURCE]`
      `[RESEARCH]`
3.2.4 The interpreter frame layout on x86-64: locals below, then the frame pointer, the method
      pointer, the constant-pool cache pointer, the monitor block, and the expression stack above.
      `[SOURCE]` `[ASM]`
3.2.5 The **constant pool cache** (`ConstantPoolCache`, `ConstantPoolCacheEntry`) as the
      resolved-reference side table the interpreter rewrites into, so a `getfield` becomes an
      offset load after first execution. `[SOURCE]` `[PROVE]`
3.2.6 **Bytecode rewriting**: the JVM rewrites `getfield` → `fast_agetfield` and friends after
      resolution — the class you run is not byte-for-byte the class you compiled. `[SOURCE]`
      `[TRAP]` `[RESEARCH]`
3.2.7 The **invocation counter** and **backedge counter** in `MethodCounters`/`MethodData`, and
      where the compilation trigger of §1.16.4 reads them. `[SOURCE]`
3.2.8 `MethodData` (the MDO) as the profile store: type profiles per call site, branch taken/not
      counts, null-seen bits, and the `ProfileData` layout. This is the object C2 reads.
      `[SOURCE]` `[PROVE]`
3.2.9 Interpreter → compiled transition and back: the method entry point in `Method::_from_
      interpreted_entry` / `_from_compiled_entry`, and the **i2c/c2i adapters** that convert
      calling conventions. `[SOURCE]` `[PROVE]`
3.2.10 Why the interpreter must exist even after everything is compiled: deoptimisation targets,
       cold code, `<clinit>`, and class-loading correctness. `[PROVE]`
3.2.11 The zero-assembler interpreter (Zero) and the C++ interpreter as the portability fallbacks,
       and their performance cost. `[RESEARCH]`
3.2.12 Measuring interpreted versus compiled: `-Xint` (interpreter only) versus `-Xcomp` (compile
       everything immediately, no profile) versus default mixed mode, and what each is actually good
       for (`-Xint` for a correctness bisect; `-Xcomp` almost never). `[FLAG]` `[NUM]` `[TRAP]`

*(12 leaves)*

## §3.3 Method dispatch, inline caches and vtables

3.3.1 `vtable` construction in `InstanceKlass`: one slot per virtual method in declaration order,
      inherited slots overwritten by overrides, so `invokevirtual` is `load klass; load vtable
      slot; call`. `[SOURCE]` `[ASM]` `[NUM]`
3.3.2 `itable` construction: one itable per implemented interface, so `invokeinterface` must first
      *find* the right itable — historically a linear scan, hence the extra cost. `[SOURCE]`
      `[NUM]`
3.3.3 **Inline caches**: the call site starts unlinked, becomes a *monomorphic* inline cache after
      the first call (a klass compare plus a direct jump), and transitions to megamorphic (a real
      vtable/itable call) when the compare fails too often. `[SOURCE]` `[PROVE]`
3.3.4 `ICBufferFull` as a safepoint cause caused by inline-cache transitions — the tell that a hot
      call site is thrashing. `[DUMP]` `[RESEARCH]`
3.3.5 **CHA** (class hierarchy analysis): C2 can devirtualise a call entirely if the loaded
      hierarchy has exactly one implementation, and installs a **dependency** so that loading a
      second implementation deoptimises the compiled method. This is speculative optimisation with
      a correctness guard, and it is the reason "the JIT can inline through interfaces". `[PROVE]`
      `[SOURCE]`
3.3.6 The performance cliff, measured: monomorphic ≈ inlined and free; bimorphic ≈ a compare and a
      branch; megamorphic ≈ an indirect call plus a likely branch misprediction and no inlining of
      the callee at all. `[NUM]` `[PROVE]` `[RESEARCH]`
3.3.7 The design consequence: a hot strategy/visitor/filter chain with many implementations is
      structurally slower than one with a dominant implementation, and no amount of `final` fixes
      it. `[PROVE]` `[TRAP]`
3.3.8 `invokespecial` and `invokestatic` need no dispatch at all; `invokedynamic` after linkage is a
      constant `MethodHandle` chain that C2 inlines through, which is why lambdas are as fast as
      inner classes once warm. `[PROVE]` `[X-REF 04]`
3.3.9 `MethodHandle` and `LambdaForm` internals: the invoker chains, `@ForceInline`/`@Hidden`
      annotations, and why method-handle code is fast only when the handle is a **constant**.
      `[TRAP]` `[RESEARCH]`

*(9 leaves)*

## §3.4 C1 and C2

3.4.1 C1's pipeline: bytecode → HIR (SSA, basic blocks) → local optimisations (constant folding,
      CSE, null-check elimination, inlining of trivial methods) → LIR → linear-scan register
      allocation → machine code. Optimised for **compile speed**. `[SOURCE]` `[RESEARCH]`
3.4.2 C1's profiling instrumentation at level 3, and why level-3 code is measurably *slower* than
      level-2 code — a fact that explains a mid-warmup throughput dip. `[PROVE]` `[NUM]`
3.4.3 C2's pipeline: bytecode → **sea of nodes** ideal graph → parsing with inlining →
      iterative GVN → loop optimisations → escape analysis → macro expansion → matching to machine
      nodes → **graph-colouring register allocation (Chaitin-Briggs)** → peephole → code emission.
      `[SOURCE]` `[RESEARCH]`
3.4.4 **Sea of nodes** explained properly: control and data edges in one graph with only the
      necessary ordering constraints, so scheduling is a late decision. This is why C2 can move code
      so aggressively and why its compile time is superlinear in method size. `[PROVE]`
3.4.5 C2's phase list as it appears in `-XX:+PrintCompilation`/IdealGraphVisualizer, and IGV as the
      tool for looking at the graph. `[RESEARCH]`
3.4.6 Loop optimisations by name: loop unrolling (`-XX:LoopUnrollLimit`, default 60), loop peeling,
      loop unswitching, loop predication (moving range checks out), iteration splitting for
      range-check elimination, and **superword/SIMD vectorisation**
      (`-XX:+UseSuperWord`, on by default). `[FLAG]` `[NUM]` `[RESEARCH]`
3.4.7 **Range-check elimination** as the reason a `for (i = 0; i < a.length; i++)` loop has no bounds
      check in the emitted code while a loop with an unprovable bound does. Show both in assembly.
      `[ASM]` `[PROVE]`
3.4.8 **Implicit null checks**: instead of a compare-and-branch, C2 relies on the hardware SIGSEGV
      from dereferencing a low address and a signal handler that deoptimises — a null check that
      costs literally zero instructions until it fires. `[PROVE]` `[ASM]` `[RESEARCH]`
3.4.9 The consequence: a `NullPointerException` thrown in a hot loop is *expensive* (signal, deopt,
      possible recompile as "trap too often"), which is a real reason not to use exceptions for
      control flow. `[PROVE]` `[TRAP]`
3.4.10 Trusted `final` fields: C2 constant-folds `static final` always, and instance `final` fields
       only in limited cases (`-XX:+TrustFinalNonStaticFields`, off by default outside the JDK)
       because reflection can change them. `[FLAG]` `[TRAP]` `[RESEARCH]`
3.4.11 Compile time as a real cost: C2 compiling a 5000-bytecode method with deep inlining can take
       hundreds of milliseconds of a compiler thread, which is why huge methods hurt startup twice
       (never inlined, and slow to compile). `[NUM]` `[PROVE]`
3.4.12 `-XX:+PrintIdeal`, `-XX:+PrintOptoAssembly`, `-XX:+PrintAssembly` with hsdis, and
       `-XX:CompileCommand=print,Class::method` as the way to actually read what C2 produced.
       `[FLAG]` `[ASM]`
3.4.13 Graal as an alternative C2 written in Java: better escape analysis (partial EA), better
       inlining heuristics, worse warmup (it must JIT itself unless AOT-compiled with libgraal).
       `[RESEARCH]`

*(13 leaves)*

## §3.5 Inlining, escape analysis and deoptimisation in depth

3.5.1 The inlining decision as an algorithm: is it hot (invocation count relative to the caller)?
      is it small enough (`MaxInlineSize`/`FreqInlineSize`)? is the callee already compiled and
      small (`InlineSmallCode`)? is the depth under `MaxInlineLevel`? is the receiver type known?
      is it recursive? Every "not inlined" message from `PrintInlining` maps to one of these.
      `[PROVE]` `[NUM]`
3.5.2 Inlining is **transitive and budgeted**: a chain of five 20-byte methods inlines; one 400-byte
      method in the middle stops the whole chain. `[PROVE]` `[NUM]`
3.5.3 The interaction with instrumentation: an APM agent that adds 50 bytecodes to every method can
      push callees past `MaxInlineSize` and silently destroy inlining across the application.
      `[TRAP]` `[PROVE]`
3.5.4 Escape states in C2: `NoEscape`, `ArgEscape` (escapes into a callee but not further),
      `GlobalEscape`. Only `NoEscape` allows scalar replacement; `ArgEscape` allows lock elision.
      `[SOURCE]` `[NUM]` `[RESEARCH]`
3.5.5 The connection-graph algorithm sketch and why it runs *after* inlining — inlining is what
      turns an `ArgEscape` into a `NoEscape`. `[PROVE]`
3.5.6 Scalar replacement in effect: the object's fields become SSA values in registers, the
      allocation disappears from the assembly, and `-XX:+PrintEliminateAllocations` proves it.
      `[FLAG]` `[ASM]` `[PROVE]`
3.5.7 What defeats escape analysis, exhaustively: storing the reference in a field or array,
      returning it, passing it to a method that is not inlined, using it as a lock that is not
      elided, `System.identityHashCode`, a virtual call that stays megamorphic, and control flow the
      analysis cannot merge (the case partial EA fixes). `[TRAP]` `[PROVE]`
3.5.8 The **reallocation on deopt** problem: if a scalar-replaced object's frame deoptimises, the VM
      must *materialise* the object and re-lock it. The deoptimisation framework does exactly this,
      which is why the optimisation is sound. `[PROVE]` `[SOURCE]` `[RESEARCH]`
3.5.9 Deoptimisation mechanics: the compiled frame is described by a **scope descriptor** (which
      bytecode index, which values are in which registers/stack slots), the VM builds interpreter
      frames from it, and execution continues. This is `Deoptimization::fetch_unroll_info` →
      `unpack_frames`. `[SOURCE]` `[PROVE]`
3.5.10 Deopt **actions**: `none` (re-execute and hope), `maybe_recompile`, `reinterpret`,
       `make_not_entrant`, `make_not_compilable`. Combined with the *reason*, this is the pair you
       read in a `LogCompilation` deopt record. `[SOURCE]` `[RESEARCH]`
3.5.11 Reading a real deoptimisation event from JFR (`jdk.Deoptimization`: method, bci, reason,
       action) and turning it into an explanation. `[DUMP]`
3.5.12 The four common real-world deopt causes: a rarely-taken branch finally taken (`unstable_if`),
       a second implementation class loaded (`class_check`), a null appearing where none had been
       seen (`null_check`), and an array index outside the profiled range (`range_check`).
       `[PROVE]`
3.5.13 Lock elision and lock coarsening as escape-analysis consequences: a lock on a non-escaping
       object is removed entirely; adjacent locks on the same object are merged into one region —
       and coarsening across a loop is why "narrow critical sections" is not universally true.
       `[X-REF 05]` `[PROVE]` `[TRAP]`
3.5.14 Why you cannot rely on any of this: it is all speculative, profile-dependent and
       version-dependent. Write clear code, measure, and treat the JIT as a very good optimiser you
       do not control. `[PROVE]` `[TRAP]`

*(14 leaves)*

## §3.6 The code cache and compiled-code lifecycle

3.6.1 An `nmethod`'s anatomy: the header, the relocation info, the constants section, the verified
      and unverified entry points, the code, the exception handler table, the **oop map set** (for
      GC), the scope descriptors (for deopt), and the dependency list (for CHA). `[SOURCE]`
3.6.2 The **oop maps** in compiled code are what make precise GC possible at safepoints: for each
      safepoint in the method, which register/stack slot holds a reference. `[PROVE]` `[SOURCE]`
3.6.3 Dependencies and invalidation: loading a class can invalidate compiled code across the whole
      JVM; the `DependencyContext` walk plus `make_not_entrant` is the mechanism. `[SOURCE]`
3.6.4 The `nmethod` state machine and **sweeping**: not-entrant code is unlinked, then reclaimed.
      The dedicated `NMethodSweeper` thread was removed in Java 20 in favour of GC-driven unloading.
      `[VERSION-TRAP]` `[RESEARCH]`
3.6.5 Code cache flushing (`-XX:+UseCodeCacheFlushing`, on by default) and what happens when it is
      disabled and the cache fills. `[FLAG]`
3.6.6 Reading `jcmd Compiler.codecache` and `Compiler.CodeHeap_Analytics`: per-heap size, used,
      free, largest free block, and the fragmentation story. `[DUMP]`
3.6.7 Code cache sizing for an instrumented or very large application, and the alarm you should have
      on `jvm_memory_used_bytes{area="nonheap",id~"CodeHeap.*"}`. `[X-REF 20]` `[NUM]`
3.6.8 Frequency-based code layout and why hot/cold splitting inside a method matters for the
      instruction cache. `[RESEARCH]` `[PROVE]`

*(8 leaves)*

## §3.7 Allocation internals

3.7.1 The emitted fast-path allocation sequence in compiled code, instruction by instruction: load
      `tlab_top`, add size, compare with `tlab_end`, branch to slow path, store new top, store the
      klass pointer and mark word, zero the fields. Roughly 10 instructions. `[ASM]` `[NUM]`
      `[PROVE]`
3.7.2 `TLAB` refill policy: `desired_size` adapts per thread from allocation history,
      `refill_waste_limit` decides retire-vs-slow-path, and `-XX:+ResizeTLAB` drives the adaptation.
      `[SOURCE]` `[NUM]` `[RESEARCH]`
3.7.3 **Heap parsability**: a retired TLAB's remaining space must be filled with a dummy
      `int[]` so the GC can walk the heap linearly. This is where "TLAB waste" physically goes.
      `[PROVE]` `[RESEARCH]`
3.7.4 The slow path: `CollectedHeap::mem_allocate` → possible GC → possible direct old-gen
      allocation for humongous objects. `[SOURCE]`
3.7.5 Object initialisation cost: zeroing is proportional to size, and for large arrays it dominates
      allocation. `-XX:+ReduceInitialCardMarks` and the JIT's elimination of redundant zeroing when
      the fields are immediately assigned. `[PROVE]` `[NUM]` `[RESEARCH]`
3.7.6 Allocation and locality: consecutive allocations from one TLAB are adjacent in memory, so
      objects allocated together are collected and accessed together. A copying collector *improves*
      locality over time; a non-moving one degrades it. `[PROVE]` `[RESEARCH]`
3.7.7 The identity hash code's interaction with allocation and moving GC: the hash must be stable
      across moves, hence storing it in the mark word on first request, hence the displaced-header
      dance while locked. `[PROVE]` `[X-REF 05]`
3.7.8 `-Xlog:gc+tlab=trace` output read line by line: fills, slow allocations, waste percentage.
      `[DUMP]`

*(8 leaves)*

## §3.8 GC barriers

3.8.1 A barrier is code the JIT and interpreter emit around heap accesses on the collector's behalf.
      Naming the barrier a collector uses is the fastest way to explain its throughput cost.
      `[PROVE]`
3.8.2 The **card-marking write barrier** (Serial, Parallel, and G1's post-barrier base): compute
      `card = (addr >> 9)` and store a byte. Two or three instructions on every reference store.
      `[ASM]` `[NUM]` `[PROVE]`
3.8.3 Card size 512 bytes → the shift of 9 → the card table is ~0.2% of the heap. Show the
      arithmetic. `[NUM]` `[PROVE]`
3.8.4 **Conditional versus unconditional** card marking, and false sharing on the card table across
      cores (`-XX:+UseCondCardMark`). `[FLAG]` `[PROVE]` `[RESEARCH]`
3.8.5 G1's **pre-barrier (SATB)**: on a reference store, log the *previous* value into a thread-local
      SATB buffer so concurrent marking cannot lose it. This is where G1's throughput cost mostly
      lives. `[PROVE]` `[ASM]`
3.8.6 G1's **post-barrier**: dirty the card and, if it crosses regions, enqueue it for the
      remembered-set update — with filters for same-region, null, and young-to-young stores.
      `[PROVE]`
3.8.7 The refinement threads that drain the dirty-card queue concurrently
      (`-XX:G1ConcRefinementThreads`), and what happens when the mutator has to help
      (`G1ConcRefinementGreenZone`/`YellowZone`/`RedZone`). `[FLAG]` `[RESEARCH]`
3.8.8 **JEP 475 (Java 24) late barrier expansion for G1**: barriers are expanded after C2's
      optimisation instead of before, cutting C2 compile time and improving generated code. A
      concrete example of "the barrier is a compiler problem". `[VERSION-TRAP]` `[RESEARCH]`
3.8.9 ZGC's **load barrier**: every reference load goes through a test of the pointer's colour bits
      and a slow path that remaps/marks. Costs on every *read*, not every write — the opposite
      trade to G1. `[PROVE]` `[ASM]`
3.8.10 ZGC's **store barrier** added by generational ZGC (JEP 439) to move marking work off the load
       path and to maintain remembered sets between generations. `[RESEARCH]` `[PROVE]`
3.8.11 Shenandoah's **load reference barrier (LRB)** and the historical Brooks forwarding pointer
       (an extra word per object, since replaced by an in-mark-word forwarding scheme).
       `[RESEARCH]` `[NUM]`
3.8.12 The barrier cost table: which collector pays on read, on write, on both, and the rough
       throughput percentage each costs. This is the honest version of "ZGC costs throughput".
       `[NUM]` `[PROVE]`
3.8.13 Why Epsilon is the throughput ceiling measurement: no barriers at all, so
       `Epsilon − G1` is your barrier + GC cost. `[PROVE]` `[NUM]`

*(13 leaves)*

## §3.9 G1 internals

3.9.1 Region metadata: `HeapRegion` with type (Free/Eden/Survivor/Old/StartsHumongous/
      ContinuesHumongous/Archive), top, bottom, end, and the `RemSet`. `[SOURCE]`
3.9.2 The **remembered set** implementation: a per-region coarse/fine/sparse three-level structure
      (sparse per-region-table, fine-grained bitmap, coarse "whole region points at me"), with
      coarsening under pressure — and the NMT `GCCardSet` category where it shows up. `[NUM]`
      `[RESEARCH]`
3.9.3 The card-based redesign of G1 remembered sets in recent releases, which cut their memory
      footprint substantially — verify against the current release notes before quoting a
      percentage. `[RESEARCH]` `[NUM]`
3.9.4 The **concurrent marking cycle** phase by phase: Initial Mark (piggybacked on a young pause),
      Root Region Scan, Concurrent Mark, Remark (STW, drains SATB buffers, reference processing,
      class unloading), Cleanup (STW, computes region liveness, frees fully-empty regions).
      `[SOURCE]` `[DUMP]`
3.9.5 **Why Remark must be STW**: SATB buffers must be drained to a fixed point, and that requires
      the mutator to stop producing them. `[PROVE]`
3.9.6 The liveness bitmaps (prev/next) and the TAMS (top-at-mark-start) pointers that let G1 treat
      everything allocated during marking as implicitly live. `[SOURCE]` `[PROVE]`
3.9.7 The **pause prediction model**: G1 keeps a decaying average of per-region evacuation cost and
      picks a collection set that fits `MaxGCPauseMillis`. `-XX:G1ConfidencePercent` and the
      "adaptive IHOP" feedback loop. `[PROVE]` `[RESEARCH]`
3.9.8 Collection set selection for mixed collections: candidates sorted by garbage ratio, capped by
      `G1MixedGCCountTarget`, filtered by `G1MixedGCLiveThresholdPercent`, stopped by
      `G1HeapWastePercent`. Walk the interaction of all four. `[NUM]` `[PROVE]`
3.9.9 Evacuation mechanics: per-thread GC allocation buffers (PLABs), copying, forwarding pointers
      installed in the mark word, and the parallel work-stealing termination protocol. `[PROVE]`
3.9.10 **Evacuation failure / to-space exhausted** in detail: the collector cannot obtain a free
       region, so it "self-forwards" objects in place, leaving the heap in a state that usually
       forces a full GC. `G1ReservePercent`/`G1HeapReservePercent` is the insurance premium.
       `[PROVE]` `[TRAP]` `[NUM]`
3.9.11 Humongous allocation path: contiguous regions, `StartsHumongous` + `ContinuesHumongous`, the
       wasted tail, eager reclaim for humongous *primitive arrays* with no incoming references
       (`-XX:+G1EagerReclaimHumongousObjects`), and the concurrent cycle a humongous allocation can
       trigger. `[NUM]` `[PROVE]`
3.9.12 G1's full GC: parallel since Java 10, mark-sweep-compact, and the flags around it. Treat
       every occurrence as an incident. `[TRAP]`
3.9.13 Class unloading in G1 happens at Remark, gated by
       `-XX:+ClassUnloadingWithConcurrentMark`. Without a concurrent cycle, metaspace is never
       reclaimed — which is how a low-allocation service can still OOM on metaspace. `[FLAG]`
       `[TRAP]` `[PROVE]`
3.9.14 **Region pinning (JEP 423, Java 22)** replacing the GC locker for JNI critical sections, so a
       `GetPrimitiveArrayCritical` no longer blocks GC for the whole heap. `[VERSION-TRAP]`
       `[RESEARCH]`
3.9.15 Reading a full G1 log for one concurrent cycle, from `Concurrent Mark Cycle` through
       `Pause Remark`, `Pause Cleanup`, to the mixed collections that follow. `[DUMP]`

*(15 leaves)*

## §3.10 ZGC internals

3.10.1 The **coloured pointer** layout: a 64-bit pointer with metadata bits (marked0, marked1,
       remapped, finalizable, plus generational bits) and the ~44 bits of address, giving the 16 TB
       heap limit. Verify the exact bit assignment against the current source before writing it.
       `[NUM]` `[RESEARCH]` `[SOURCE]`
3.10.2 **Multi-mapping** (the historical implementation): the same physical page mapped at several
       virtual addresses so that a coloured pointer dereferences correctly without masking — and its
       replacement by a pointer-masking scheme in newer releases. `[RESEARCH]` `[VERSION-TRAP]`
3.10.3 The consequence for observability: RSS accounting for a multi-mapped ZGC heap confuses naive
       tools, which is why ZGC heaps historically appeared to use 3× memory in `top`. `[TRAP]`
       `[NUM]` `[RESEARCH]`
3.10.4 The **load barrier** in emitted code: test the loaded pointer's colour against the current
       "good colour" mask, and on mismatch call the slow path to mark and/or remap, then **self-heal**
       the field so the next load is fast. Self-healing is the key idea. `[ASM]` `[PROVE]`
3.10.5 The GC cycle: Pause Mark Start (STW, roots) → Concurrent Mark → Pause Mark End → Concurrent
       Process References → Concurrent Reset Relocation Set → Pause Relocate Start → Concurrent
       Relocate. Only three short pauses, all root-set bounded. `[SOURCE]` `[NUM]`
3.10.6 The **forwarding tables** used during relocation, and why ZGC does not need a Brooks pointer
       word per object. `[PROVE]`
3.10.7 Page types: small (2 MB, objects ≤ 256 KB), medium (32 MB, objects ≤ 4 MB), large (N × 2 MB,
       one object). Large pages are never relocated. `[NUM]` `[RESEARCH]`
3.10.8 **Generational ZGC** structure: young and old collections with independent marking/relocation
       metadata bits, a store barrier maintaining remembered sets, and the ability to run a young
       collection while an old one is in progress. `[SOURCE]` `[RESEARCH]`
3.10.9 Concurrent **stack processing** (JEP 376) — thread stacks scanned concurrently using stack
       watermarks, which is what removed the last heap-size-independent-but-thread-count-dependent
       pause. `[RESEARCH]` `[PROVE]`
3.10.10 The allocation-stall mechanism and how to read `Allocation Stall` events in the log and in
        JFR (`jdk.ZAllocationStall`). `[DUMP]` `[RESEARCH]`
3.10.11 Why ZGC cannot use compressed oops: the metadata bits occupy the space a 32-bit reference
        would need. Quantify the footprint penalty on a 10 GB heap with many references. `[NUM]`
        `[PROVE]`
3.10.12 ZGC's class unloading and reference processing, both concurrent. `[RESEARCH]`

*(12 leaves)*

## §3.11 Shenandoah, Parallel, Serial and Epsilon internals

3.11.1 Shenandoah's cycle: Init Mark (STW) → Concurrent Mark → Final Mark (STW) → Concurrent
       Cleanup → Concurrent Evacuation → Init Update Refs (STW) → Concurrent Update References →
       Final Update Refs (STW) → Concurrent Cleanup. `[SOURCE]` `[RESEARCH]`
3.11.2 The **Brooks pointer** historically: an extra word per object holding a forwarding pointer,
       dereferenced on every access. Its removal in favour of the load reference barrier plus
       mark-word forwarding, and the footprint saving that produced. `[NUM]` `[VERSION-TRAP]`
       `[RESEARCH]`
3.11.3 The **load reference barrier** and why it lets Shenandoah keep compressed oops where ZGC
       cannot. `[PROVE]`
3.11.4 Shenandoah heuristics (`adaptive`, `static`, `compact`, `aggressive`) and modes (`satb`,
       `iu`, `passive`, `generational`), with the failure mode of each. `[FLAG]` `[RESEARCH]`
3.11.5 Degenerated GC and Full GC as Shenandoah's fallbacks when the mutator outruns the collector —
       the analogue of G1's evacuation failure. `[TRAP]` `[RESEARCH]`
3.11.6 **Parallel GC** internals: `PSYoungGen` copying scavenge with per-thread PLABs and
       work-stealing, `PSOldGen` mark-summary-compact, and the adaptive size policy that resizes
       Eden/survivors to hit `GCTimeRatio`/`MaxGCPauseMillis`. `[SOURCE]` `[NUM]`
3.11.7 `-XX:-UseAdaptiveSizePolicy` as the flag that turns off the resizing that makes Parallel's
       behaviour hard to reason about. `[FLAG]`
3.11.8 **Serial GC** internals: `DefNew` copying young + `TenuredGeneration` mark-sweep-compact, one
       thread, no barriers beyond the card table. The whole collector is a few thousand lines, which
       is why it is the right teaching example and a genuinely good small-container choice.
       `[SOURCE]` `[PROVE]`
3.11.9 **Epsilon** internals: a bump allocator over the whole heap, `CollectedHeap` implemented as
       "throw OOM". Its use as a measurement baseline and in single-shot jobs. `[SOURCE]`
3.11.10 The historical **CMS** in one paragraph so you can answer the question and say why it is
        gone: concurrent mark-sweep with incremental update, no compaction, concurrent mode failure
        falling back to a single-threaded full compaction, and unbounded fragmentation. Removed in
        Java 14. `[VERSION-TRAP]` `[PROVE]`
3.11.11 Azul C4 and the pauseless-collector lineage as the ancestor of ZGC's ideas, for context.
        `[RESEARCH]`

*(11 leaves)*

## §3.12 Metaspace internals

3.12.1 The pre-JEP-387 allocator and its problems: chunk sizes in a few fixed classes, per-loader
       waste, and memory that was never returned to the OS. `[RESEARCH]`
3.12.2 **Elastic Metaspace (JEP 387, Java 16)**: a **buddy allocator** over 4 MB *root chunks*,
       splitting in halves down to 1 KB, with per-classloader arenas allocating by pointer bump
       within a chunk. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.12.3 Commit-on-demand at page granularity plus **uncommitting** of unused chunk space, which is
       what "elastic" means and why metaspace RSS can now go down. `[PROVE]`
3.12.4 `MetaspaceReclaimPolicy` (`balanced` default, `aggressive`, `none`) as the knob.
       `[FLAG]` `[RESEARCH]`
3.12.5 The two limits: the absolute `MaxMetaspaceSize`, and the **GC threshold** (`MetaspaceSize`,
       grown/shrunk by `MinMetaspaceFreeRatio`/`MaxMetaspaceFreeRatio`) that triggers a
       `Metadata GC Threshold` collection. Misreading `MetaspaceSize` as "initial size" is the
       classic error. `[TRAP]` `[NUM]` `[SOURCE]`
3.12.6 The **class space** as a separate contiguous reservation (`CompressedClassSpaceSize`,
       default 1 GB) holding only `Klass` structures so their addresses fit in 32 bits — the
       mechanism behind compressed class pointers. `[NUM]` `[PROVE]`
3.12.7 What compact object headers change here: the klass pointer is narrowed further and folded
       into the mark word, which constrains the class space size. `[RESEARCH]`
3.12.8 `ClassLoaderData` as the arena owner: metaspace is freed **only** when a whole loader dies,
       which is the implementation reason behind the classloader-leak model in §1.7.13. `[PROVE]`
3.12.9 Reading `jcmd VM.metaspace` in full: usage by chunk-level, per-loader breakdown, waste,
       commit/reserve, and the `Both` totals. `[DUMP]`
3.12.10 Metaspace fragmentation as a real phenomenon: many small loaders, each holding a partially
        used chunk. `[PROVE]`

*(10 leaves)*

## §3.13 Safepoint and handshake internals

3.13.1 The polling page mechanism: a page the VM mprotects to `PROT_NONE`; the JIT emits
       `test %eax, (poll_page)` at poll sites; the resulting SIGSEGV is caught and routed to
       `SafepointSynchronize::block`. One instruction on the fast path. `[ASM]` `[SOURCE]`
       `[PROVE]`
3.13.2 **Thread-local polling (JEP 312)**: the poll dereferences a *per-thread* pointer
       (`JavaThread::_poll_page`) which the VM can point at either an always-guarded or an
       always-unguarded page, so one thread can be stopped without stopping all. `[SOURCE]`
       `[PROVE]` `[RESEARCH]`
3.13.3 `SafepointSynchronize::begin/end` and the thread state machine
       (`_thread_in_java`, `_thread_in_vm`, `_thread_in_native`, `_thread_blocked`,
       plus the `_trans` variants) — which states are "safepoint safe" and which must be stopped.
       `[SOURCE]` `[PROVE]`
3.13.4 Why a thread `_thread_in_native` is already safe: it holds no oops in registers and cannot
       touch the heap without transitioning back, at which point it blocks. `[PROVE]`
3.13.5 Poll placement rules: at every return and at every non-counted loop backedge. Counted `int`
       loops historically had no poll, which is the textbook long-TTSP cause; long-counted loops got
       polls later. Verify the current behaviour before writing it. `[TRAP]` `[RESEARCH]`
3.13.6 `-XX:+UseCountedLoopSafepoints` and `-XX:LoopStripMiningIter` (default 1000) as the modern
       fix: strip-mine a counted loop into chunks with a poll between them. `[FLAG]` `[NUM]`
       `[RESEARCH]`
3.13.7 The GC locker and JNI critical sections as a historical source of "GC is blocked by a
       thread", replaced for G1 by region pinning (JEP 423, Java 22). `[VERSION-TRAP]`
       `[RESEARCH]`
3.13.8 Handshake operations in current use: per-thread stack scanning (ZGC), biased-lock revocation
       (historical), `Thread.getStackTrace` for one thread, and virtual-thread mount/unmount
       bookkeeping. `[RESEARCH]`
3.13.9 Reading `-Xlog:safepoint+stats=debug`: the per-operation table with `[threads: total
       initially_running wait_to_block]` and the `[time: spin block sync cleanup vmop]` breakdown.
       This decomposes TTSP into where it actually went. `[DUMP]` `[NUM]`
3.13.10 The "cleanup" VM operation that runs at `GuaranteedSafepointInterval`: deflating idle
        monitors, updating inline caches, and nmethod housekeeping. `[SOURCE]` `[RESEARCH]`

*(10 leaves)*

## §3.14 Exception handling and stack unwinding internals

3.14.1 `athrow` semantics: search the current method's exception table for a handler whose
       `[start_pc, end_pc)` covers the current bci and whose `catch_type` matches; if none, pop the
       frame and repeat in the caller. `[SOURCE]` `[PROVE]`
3.14.2 Compiled-code exception dispatch: the `nmethod`'s exception handler table plus
       `OptoRuntime::handle_exception`, and the fact that an exception crossing a compiled frame is
       far more expensive than a local branch. `[PROVE]` `[NUM]`
3.14.3 `fillInStackTrace` walks the stack and records `(method, bci)` pairs lazily converted to
       `StackTraceElement`s on demand — which is why *constructing* an exception costs
       proportionally to stack depth and *throwing* it does not. `[PROVE]` `[NUM]` `[X-REF 03]`
3.14.4 The **stackless exception** optimisation: `-XX:-OmitStackTraceInFastThrow` (the flag is on by
       default) makes C2 replace a repeatedly-thrown implicit exception (NPE, AIOOBE, ArithmeticE,
       ClassCastE, ArrayStoreE) with a **preallocated, stack-trace-less** instance. This is why
       production logs contain `java.lang.NullPointerException` with **no stack trace at all**, and
       it is one of the most confusing production symptoms in Java. `[FLAG]` `[TRAP]` `[PROVE]`
       `[RESEARCH]`
3.14.5 Overriding `fillInStackTrace` or using the four-arg `Exception(msg, cause, suppression,
       writableStackTrace)` constructor for control-flow exceptions in hot paths — the legitimate
       optimisation, and why it is almost always the wrong design anyway. `[X-REF 03]` `[TRAP]`
3.14.6 **Helpful NullPointerExceptions** (JEP 358, Java 14; on by default since 15): the message
       naming the exact expression, computed by re-reading the bytecode at throw time. `[NUM]`
       `[VERSION-TRAP]`
3.14.7 `StackWalker` (JEP 259, Java 9) as the lazy, cheap alternative to
       `Thread.currentThread().getStackTrace()`, with `RETAIN_CLASS_REFERENCE` and
       `SHOW_HIDDEN_FRAMES`. `[X-REF 03]` `[RESEARCH]`
3.14.8 Frame elision by inlining: an inlined callee has no physical frame, so the JVM must
       reconstruct it from scope descriptors for the stack trace. This is why stack traces stay
       correct despite inlining, and it is not free. `[PROVE]`
3.14.9 `try`/`finally` compiled as duplicated blocks plus a catch-all handler entry, and
       try-with-resources' generated suppression handling. `[BYTECODE]` `[X-REF 03]`
3.14.10 `StackOverflowError` handling: the guard pages (yellow/red zone), the signal handler that
        converts the fault into an `Error`, and the reserved zone
        (`-XX:StackReservedPages`) that gives critical sections room to unwind. `[SOURCE]`
        `[RESEARCH]` `[NUM]`

*(10 leaves)*

## §3.15 JNI, FFM and native interop internals

3.15.1 JNI's model: `JNIEnv*`, local and global references, the reference table, `PushLocalFrame`/
       `PopLocalFrame`, and the local-reference-table-overflow crash that follows a loop that
       forgets `DeleteLocalRef`. `[SOURCE]` `[TRAP]`
3.15.2 Why a JNI call costs: a state transition (`_thread_in_java` → `_thread_in_native`), a stub
       to marshal arguments, loss of inlining across the boundary, and a safepoint interaction on
       return. Order of magnitude tens of nanoseconds for a trivial call. `[NUM]` `[PROVE]`
3.15.3 `GetPrimitiveArrayCritical`/`ReleasePrimitiveArrayCritical` and the GC locker: the historical
       "a JNI critical section blocks GC" behaviour, and G1 region pinning (JEP 423) replacing it.
       `[VERSION-TRAP]` `[RESEARCH]`
3.15.4 JNI global references and weak globals as **GC roots**, and their appearance in the thread
       dump header and in a heap dump's root list — a real leak vector from native libraries.
       `[TRAP]` `[DUMP]`
3.15.5 `System.loadLibrary` mechanics, `java.library.path`, and `UnsatisfiedLinkError` diagnosis.
       Native libraries are loaded per-classloader, so redeploying a WAR that loads a library fails
       the second time. `[TRAP]` `[RESEARCH]`
3.15.6 **JEP 472 (Java 24)**: JNI use produces warnings by default and requires
       `--enable-native-access`, aligning JNI with the FFM restriction model. `[VERSION-TRAP]`
       `[RESEARCH]`
3.15.7 The **FFM API** (JEP 454, final Java 22): `Linker`, `SymbolLookup`, `FunctionDescriptor`,
       `MemorySegment`, `MemoryLayout`, `VarHandle` access, and downcall/upcall handles. `[BUILD]`
       `[RESEARCH]`
3.15.8 `Arena` lifetimes as the deterministic-deallocation model: `Arena.global()` (never freed),
       `Arena.ofAuto()` (GC-managed), `Arena.ofConfined()` (single-thread, closed deterministically),
       `Arena.ofShared()`. Compare with `DirectByteBuffer`'s GC-dependent freeing. `[PROVE]`
       `[RESEARCH]`
3.15.9 Why FFM is faster than JNI in principle: the downcall handle is a `MethodHandle` C2 can
       inline through and specialise, versus JNI's opaque stub. Present this as a mechanism
       argument, not a benchmark claim, unless you have a source. `[PROVE]` `[TRAP]`
       `[RESEARCH]`
3.15.10 `jextract` as the header-to-bindings generator, and the restricted-method warning model
        (`--enable-native-access=ALL-UNNAMED`). `[RESEARCH]`
3.15.11 `sun.misc.Unsafe`'s memory-access methods deprecated (JEP 471, Java 23) and warning by
        default (JEP 498, Java 24), with `VarHandle` and `MemorySegment` as the two replacements.
        `[VERSION-TRAP]` `[X-REF 05]`
3.15.12 Diagnosing a crash in native code: the `hs_err` `Problematic frame` line, `C  [libfoo.so+...]`
        versus `J  com.acme.Foo.bar`, and the `Native frames`/`Java frames` split. `[DUMP]`
        `[PROVE]`

*(12 leaves)*

## §3.16 CDS, AOT and the Leyden machinery

3.16.1 What a CDS archive physically is: a memory-mappable image of `InstanceKlass` structures and
       related metadata, laid out so it can be mapped at a fixed address and shared **read-only
       between processes**. `[SOURCE]` `[PROVE]`
3.16.2 The two savings: no parse/verify cost per class, and one physical copy of the metadata shared
       across every JVM on the host — which matters enormously when you run 50 containers of the
       same image on one node. `[PROVE]` `[NUM]`
3.16.3 Why the archive is fragile: it records the classpath *string*, the JDK build, and the
       relocation base. Any mismatch silently disables it under `-Xshare:auto`. `[TRAP]`
3.16.4 Archived heap objects (integer cache, module graph, interned strings) as the second-order
       optimisation, and why they constrain GC choice (archived regions must be mappable).
       `[RESEARCH]`
3.16.5 Dynamic CDS (JEP 350): the app archive layered on the default base archive; `-XX:+Record
       DynamicDumpInfo` plus `jcmd VM.cds dynamic_dump` as the alternative to
       `ArchiveClassesAtExit`. `[FLAG]` `[RESEARCH]`
3.16.6 **JEP 483 AOT class loading and linking**: stores classes already *loaded and linked*, not
       merely parsed — the difference from CDS stated precisely. `[VERSION-TRAP]` `[PROVE]`
       `[RESEARCH]`
3.16.7 The training-run model: `-XX:AOTMode=record` → `-XX:AOTConfiguration` →
       `-XX:AOTMode=create` → `-XX:AOTCache`, collapsed to `-XX:AOTCacheOutput` by JEP 514
       (Java 25). `[FLAG]` `[VERSION-TRAP]` `[RESEARCH]`
3.16.8 **JEP 515 AOT method profiling**: the cache carries MDO-equivalent profiles so C2 can compile
       optimised code immediately rather than after 15 000 invocations. This is the first mechanism
       that attacks *warmup* rather than *startup*. `[PROVE]` `[RESEARCH]`
3.16.9 What Leyden explicitly does not do (yet): full AOT machine code in the mainline JVM, and the
       closed-world assumption GraalVM makes. Keep the two projects distinct in your answer.
       `[TRAP]` `[RESEARCH]`
3.16.10 GraalVM native image's build pipeline: points-to analysis over the closed world →
        initialisation at build time → heap snapshotting → AOT compilation → the SubstrateVM runtime
        (its own GC: serial or G1). Naming SubstrateVM is the detail that shows you know it is a
        different runtime, not "Java compiled to native". `[PROVE]` `[RESEARCH]`
3.16.11 Reachability metadata: `reflect-config.json`, `resource-config.json`, `proxy-config.json`,
        `serialization-config.json`, the tracing agent that generates them, and the shared
        reachability-metadata repository. `[RESEARCH]`
3.16.12 `--initialize-at-build-time` and the class-initialisation hazards it creates (a static field
        capturing build-machine state, a `SecureRandom` seeded at build, an open file handle
        snapshotted). `[TRAP]` `[RESEARCH]`

*(12 leaves)*

## §3.17 Instrumentation, JVMTI and agent internals

3.17.1 **JVMTI** as the native profiling/debugging interface: capabilities, event callbacks, and the
       fact that some capabilities (e.g. `can_generate_all_class_hook_events`) must be requested in
       the `OnLoad` phase or never. `[SOURCE]` `[RESEARCH]`
3.17.2 The JVMTI event inventory worth knowing: `ClassFileLoadHook`, `VMInit`, `VMDeath`,
       `ThreadStart`, `GarbageCollectionStart/Finish`, `ObjectFree`, `MonitorContendedEnter`,
       `Exception`, `SingleStep`, `CompiledMethodLoad` (which is what perf-map agents use for
       symbols). `[RESEARCH]`
3.17.3 `java.lang.instrument` as the Java-level layer on top: the `premain`/`agentmain` contract,
       the `Premain-Class`/`Agent-Class`/`Can-Redefine-Classes`/`Can-Retransform-Classes` manifest
       attributes, and `ClassFileTransformer`. `[BUILD]`
3.17.4 Retransformation versus redefinition, and the strict limits: method bodies only — no schema
       change, no hierarchy change, no method addition. `[TRAP]`
3.17.5 The cost model: `ClassFileLoadHook` makes every class pass through every transformer;
       retransforming 10 000 loaded classes is a long safepoint-heavy operation. `[NUM]` `[PROVE]`
3.17.6 `AsyncGetCallTrace` as the unsupported-but-universal profiling entry point, its
       `ASGCT_FAILURE` reasons, and JEP 435's proposed supported replacement. `[RESEARCH]`
3.17.7 Why an agent can break the JIT: added bytecode inflates method size past inline thresholds,
       and try/finally wrappers create exception edges that inhibit optimisation. `[PROVE]`
       `[TRAP]`
3.17.8 Debugging support: JDWP (`-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,
       address=*:5005`), and the fact that a breakpoint deoptimises the containing method and
       disables some optimisations *for the rest of the run*. Never benchmark under a debugger.
       `[FLAG]` `[TRAP]` `[PROVE]`
3.17.9 Serviceability agent (SA) internals: reading a live process or core file by walking VM
       structures from outside, which is why `jhsdb` works on a dead process and `jcmd` does not.
       `[PROVE]` `[RESEARCH]`
3.17.10 The attach mechanism on Linux: `/tmp/.java_pid<pid>` unix socket, the `SIGQUIT`-triggered
        attach listener, and `-XX:+DisableAttachMechanism` / read-only `/tmp` / a different PID
        namespace as the three things that break it. `[TRAP]` `[X-REF 19]` `[RESEARCH]`

*(10 leaves)*

## §3.18 The JVM's own concurrency machinery

3.18.1 One paragraph on monitor implementation, since §1.10.3 already gave the mark word: stack
       locking for uncontended cases, inflation to an `ObjectMonitor` (`_owner`, `_recursions`,
       `_EntryList`, `_cxq`, `_WaitSet`) on contention or `wait()`, and deflation at a cleanup
       safepoint. Full treatment in guide 05. `[X-REF 05]` `[SOURCE]`
3.18.2 `ObjectSynchronizer` and the monitor table redesign that compact object headers required
       (there is no room for a monitor pointer in an 8-byte header). This is the concrete cost of
       JEP 519 that nobody mentions. `[RESEARCH]` `[PROVE]`
3.18.3 `Mutex`/`Monitor` as the VM's *internal* locks (distinct from Java monitors), the lock
       ranking system that prevents VM deadlock, and their appearance in `hs_err`. `[SOURCE]`
       `[DUMP]`
3.18.4 `os::PlatformEvent` / futex as the parking primitive underneath `LockSupport.park`.
       `[X-REF 05]` `[X-REF 11]`
3.18.5 Virtual-thread internals at the JVM level: `Continuation` as a VM-supported delimited
       continuation, `StackChunk` objects on the **heap** holding frozen frames, freeze/thaw with
       lazy copying, and the fact that an unmounted virtual thread's stack is heap data a GC must
       trace. Mechanism only; API and pinning in guide 05. `[X-REF 05]` `[SOURCE]` `[RESEARCH]`
3.18.6 The GC consequence of virtual threads: a million parked virtual threads are a million heap
       objects with stack chunks, so "virtual threads are cheap" is a *heap* statement, not a "free"
       statement. `[NUM]` `[PROVE]` `[X-REF 05]`
3.18.7 `jdk.VirtualThreadPinned`, `jdk.VirtualThreadSubmitFailed` JFR events and
       `jcmd Thread.dump_to_file -format=json` as the JVM-level observability for them.
       `[X-REF 05]` `[DUMP]`

*(7 leaves)*

## §3.19 Reference processing and string internals

3.19.1 `Reference` discovery during marking: the `DiscoveredList` chain threaded through the
       `discovered` field of each `Reference`, per reference type, per GC worker. `[SOURCE]`
3.19.2 The processing order and why it must be that order: soft (clear per policy) → weak (clear) →
       final (enqueue for finalization, resurrecting the referent for one cycle) → phantom (enqueue
       after finalization). `[PROVE]` `[SOURCE]`
3.19.3 The `Reference Handler` thread and the `ReferenceQueue` hand-off; `Common-Cleaner` as the
       shared `Cleaner` thread. `[SOURCE]`
3.19.4 Reference processing as a **pause contributor**: `-XX:+ParallelRefProcEnabled`,
       `-XX:ReferencesPerThread`, and the `Reference Processing` line in a G1 Remark pause. A heap
       with millions of weak references has a long Remark. `[FLAG]` `[DUMP]` `[PROVE]`
3.19.5 `SoftReference` clearing policy in the source: `SoftRefLRUPolicyMSPerMB` × free MB, with the
       policy consulted at each GC and *all* softs cleared before OOM. `[SOURCE]` `[NUM]`
3.19.6 **String interning** internals: the native `StringTable` hash table, `String.intern()` as a
       native call that inserts or returns, `-XX:StringTableSize` (default 65536), the table's
       weak references so interned strings can still be collected, and
       `-XX:+PrintStringTableStatistics`. `[FLAG]` `[NUM]` `[X-REF 03]` `[RESEARCH]`
3.19.7 Why mass interning is a bad idea: it is a native hash table with a fixed bucket count, a
       global lock on insert historically, and objects that live as long as the table.
       `[TRAP]` `[PROVE]`
3.19.8 **String deduplication** internals: the GC queues candidate `String`s during young
       collections, a dedup thread hashes the `byte[]` and replaces duplicates with a shared array.
       `-XX:StringDeduplicationAgeThreshold` (default 3),
       `-XX:+PrintStringDeduplicationStatistics`/`-Xlog:stringdedup*`. `[FLAG]` `[NUM]`
       `[RESEARCH]`
3.19.9 Dedup versus intern versus compact strings — three different mechanisms with three different
       owners (GC, user code, compiler/runtime layout). Confusing them is common. `[TRAP]`
       `[X-REF 03]`
3.19.10 The symbol table (`Symbol` objects for class/method/field names) as a separate, native,
        refcounted table in metaspace, and `-XX:+PrintSymbolTableStatistics`. `[RESEARCH]`

*(10 leaves)*

## §3.20 Heap dump and thread dump formats

3.20.1 The **HPROF binary format**: a header, then a stream of tagged records —
       `HPROF_UTF8`, `HPROF_LOAD_CLASS`, `HPROF_FRAME`, `HPROF_TRACE`, `HPROF_HEAP_DUMP_SEGMENT`
       containing sub-records `ROOT_JNI_GLOBAL`, `ROOT_JAVA_FRAME`, `ROOT_STICKY_CLASS`,
       `ROOT_THREAD_OBJ`, `GC_CLASS_DUMP`, `GC_INSTANCE_DUMP`, `GC_OBJ_ARRAY_DUMP`,
       `GC_PRIM_ARRAY_DUMP`. Knowing the root record types is knowing what "GC root" means
       concretely. `[SOURCE]` `[RESEARCH]`
3.20.2 Why a heap dump pauses the JVM and how long: it walks the entire live object graph at a
       safepoint and writes it, so the pause is proportional to live-set size, and the file to
       live-set bytes. `[NUM]` `[PROVE]`
3.20.3 The dominator-tree computation MAT performs on load (Lengauer-Tarjan), why it takes minutes
       on a large dump, and the index files it leaves behind. `[NUM]` `[RESEARCH]`
3.20.4 Retained set, retained heap and the difference from "everything this object references" —
       with a worked two-parent example proving why they differ. `[PROVE]` `[NUM]`
3.20.5 What a heap dump **cannot** tell you: where an object was allocated (no allocation stack),
       how long it has lived, or how often it is accessed. JFR `jdk.OldObjectSample` answers the
       first. `[TRAP]` `[PROVE]`
3.20.6 The **thread dump text format** field by field, including `nid` (native thread id, hex),
       `tid`, `prio`/`os_prio`, `[0x...]` stack base, the `java.lang.Thread.State` line, and the
       `- locked`/`- waiting on`/`- parking to wait for` annotations. `[DUMP]` `[X-REF 05]`
3.20.7 The JSON thread dump (Java 21): `threadDumps[].threadContainers[]` reflecting the structured
       concurrency tree, and the fields available per thread. `[DUMP]` `[X-REF 05]` `[RESEARCH]`
3.20.8 Getting a thread dump when `jstack` cannot attach: `kill -3 <pid>` (SIGQUIT) writes it to the
       process's stdout — which in a container means the pod log. `[X-REF 11]` `[TRAP]`

*(8 leaves)*

## §3.21 Reading the JVM's own logs and crash artifacts

3.21.1 Unified logging internals: tag sets, levels (`error`, `warning`, `info`, `debug`, `trace`),
       outputs (`stdout`, `stderr`, `file=`), and `-Xlog:help` / `jcmd VM.log list` to enumerate
       every available tag at runtime. `[FLAG]` `[DUMP]`
3.21.2 Changing logging **at runtime** with `jcmd VM.log output=... what=gc*=debug` — no restart
       required, which is the answer to "we do not have GC logs on this pod". `[DUMP]` `[PROVE]`
3.21.3 The `hs_err_pid.log` walkthrough, section by section, on a real file: the signal/`siginfo`,
       the `Problematic frame`, the register dump, the top-of-stack hex, the instruction bytes, the
       Java frames versus native frames, the thread list, the VM state, the mutex list, the heap
       summary, metaspace, the code cache, `Compilation events`, `GC Heap History`,
       `Deoptimization events`, `Internal exceptions`, `VM Arguments`, `Environment Variables`,
       `/proc/meminfo`, and the container information block. `[DUMP]` `[RESEARCH]`
3.21.4 What each common `Problematic frame` prefix means: `C` native code, `J` compiled Java, `j`
       interpreted Java, `V` JVM code, `v` VM-generated stub. This four-letter code is the first
       branch in a crash diagnosis. `[DUMP]` `[NUM]`
3.21.5 `siginfo: si_signo: 11 (SIGSEGV), si_code: 1 (SEGV_MAPERR), si_addr: 0x0000000000000000` read
       literally: a null dereference in native code. Contrast with `si_addr` at a plausible heap
       address (memory corruption). `[DUMP]` `[PROVE]`
3.21.6 The `GC Heap History` block as the last GC log you have when GC logging was not enabled.
       `[DUMP]` `[PROVE]`
3.21.7 Core dumps: `ulimit -c`, `/proc/sys/kernel/core_pattern`,
       `-XX:+CreateCoredumpOnCrash`, and `jhsdb jstack --core core --exe java` to get Java frames
       out of one. `[X-REF 11]` `[RESEARCH]`
3.21.8 When to file a JVM bug versus when to fix your code: reproducibility, a clean `-Xint` run
       (suggests JIT), a clean run with a different collector (suggests GC), and no native agent or
       JNI in the stack. `[PROVE]`

*(8 leaves)*

---

**PART 3 total: 10+12+9+13+14+8+8+13+15+12+11+10+10+10+12+12+10+7+10+8+8 = 222 leaves**

---

# PART 4 — BUILD IT

Every `[BUILD]` leaf ships complete, compiling Java 21 and is followed by a **Diff vs the real one**
table covering at minimum: correctness cases skipped, error handling, performance techniques, spec
conformance, threading, and *why the JVM bothers*. The point of this part is that a subsystem you
have implemented badly you understand well.

## §4.1 A class file parser

4.1.1 `ClassFileReader` — a `DataInputStream`-based parser reading magic, versions, the constant
      pool (all 17 tags, including the two-slot `Long`/`Double` rule), access flags, this/super,
      interfaces, fields, methods and attributes into records. `[BUILD]`
4.1.2 Modified-UTF-8 decoding done correctly, including the `0xC0 0x80` NUL and surrogate-pair
      cases. `[BUILD]` `[PROVE]`
4.1.3 A descriptor parser turning `(Ljava/lang/String;[IJ)Ljava/util/List;` into a readable
      signature, and a `Signature`-attribute parser for the generic form. `[BUILD]`
4.1.4 A `javap`-lite that prints the constant pool, the method table with flags, and the exception
      table. `[BUILD]`
4.1.5 Version reporting: print "compiled by Java N" from the major version, and refuse anything above
      a configurable ceiling with the same message shape as `UnsupportedClassVersionError`.
      `[BUILD]` `[NUM]`
4.1.6 A jar scanner that reports the class-file version histogram of a dependency tree — a genuinely
      useful tool for a migration. `[BUILD]` `[PROVE]`
4.1.7 Diff vs the real one: `java.lang.classfile` (JEP 484) versus ASM versus your parser —
      streaming vs tree API, constant-pool sharing, `StackMapTable` generation, attribute
      round-tripping, and the writer side you did not implement.

*(7 leaves)*

## §4.2 A bytecode interpreter

4.2.1 `Frame` — an `int[]` locals array (with the two-slot rule for `long`/`double`), an operand
      stack, a pc, and a method reference. `[BUILD]`
4.2.2 A `switch`-based interpreter covering the arithmetic, load/store, stack, comparison and
      control-flow opcodes, enough to run a recursive `fib` and a loop. `[BUILD]` `[PROVE]`
4.2.3 Add `invokestatic` with a call stack of frames, then `invokevirtual` with a vtable built from
      your parsed class hierarchy. `[BUILD]`
4.2.4 Add object allocation (`new`, `getfield`, `putfield`) with a simple heap as an
      `ArrayList<Object[]>`, and prove field defaults are zeroed. `[BUILD]` `[PROVE]`
4.2.5 Add `athrow` and the exception table search, including the propagate-up-the-frames loop.
      `[BUILD]` `[PROVE]`
4.2.6 Add an invocation counter and a "compile" step that replaces a hot method with a Java lambda —
      a two-tier JIT in miniature, demonstrating the profile-then-specialise idea. `[BUILD]`
      `[PROVE]`
4.2.7 Measure your interpreter against real JVM execution of the same method and explain the 100×+
      gap in terms of dispatch, boxing and no register allocation. `[NUM]` `[PROVE]`
4.2.8 Diff vs the real one: template generation, top-of-stack caching, bytecode rewriting, the
      constant-pool cache, verification, safepoint polls, oop maps, exact GC integration, and the
      three tiers you did not build.

*(8 leaves)*

## §4.3 Class loaders

4.3.1 `DirectoryClassLoader extends ClassLoader` overriding **`findClass`** (not `loadClass`),
      reading bytes and calling `defineClass`. `[BUILD]`
4.3.2 Prove parent-first delegation by loading a class that also exists on the parent's path, then
      switch to a parent-last loader and observe the difference. `[BUILD]` `[PROVE]`
4.3.3 Demonstrate `(name, loader)` identity: load the same class file with two loaders and produce
      the `ClassCastException: com.acme.Order cannot be cast to com.acme.Order`. `[BUILD]`
      `[PROVE]` `[TRAP]`
4.3.4 A plugin loader: an isolated child-first loader per plugin jar, an interface loaded by the
      shared parent, and a clean unload demonstrated by dropping every reference and forcing a GC.
      `[BUILD]`
4.3.5 **Reproduce a classloader leak on purpose**: a plugin that registers a `ThreadLocal` on a
      shared pool thread, then show the loader surviving in a heap dump and the metaspace figure
      growing across ten reload cycles. `[BUILD]` `[PROVE]` `[TRAP]`
4.3.6 Then fix it, and prove the fix with `jcmd VM.classloaders` counts before and after.
      `[BUILD]` `[PROVE]`
4.3.7 A `registerAsParallelCapable` variant and a measurement of concurrent load throughput with and
      without it. `[BUILD]` `[NUM]`
4.3.8 `MethodHandles.Lookup.defineHiddenClass` used to spin a class from generated bytes, and
      contrast its unloadability with a full loader. `[BUILD]` `[RESEARCH]`
4.3.9 Diff vs the real one: `SystemDictionary`, loading constraints, run-time packages, module
      layers, protection domains, the `defineClass` security checks, and parallel-capable locking.

*(9 leaves)*

## §4.4 Garbage collectors from scratch

4.4.1 A tiny heap model: a `byte[]` heap, an object header (mark bit, class id, size), a bump
      allocator, and roots as an explicit list. `[BUILD]`
4.4.2 `MarkSweepCollector` — mark from roots (explicit stack, not recursion), sweep into a free
      list, and report fragmentation. `[BUILD]` `[PROVE]`
4.4.3 `CopyingCollector` (Cheney's algorithm) — semispaces, scan/free pointers, forwarding pointers
      in the header, and the proof that cost is O(live). `[BUILD]` `[PROVE]`
4.4.4 `MarkCompactCollector` — the two-finger or Lisp2 sliding compactor, showing why compaction
      costs more than copying but needs no spare semispace. `[BUILD]` `[PROVE]`
4.4.5 A **generational** collector on top: an Eden, two survivors, an old space, a tenuring
      threshold, and a **card table** with a write barrier. Prove that removing the barrier loses
      objects. `[BUILD]` `[PROVE]` `[TRAP]`
4.4.6 A **tri-colour concurrent marker** with a mutator thread, demonstrating the lost-object bug,
      then fixing it with an SATB pre-barrier and proving the fix. `[BUILD]` `[PROVE]`
4.4.7 A **region-based** collector with per-region liveness and garbage-first collection-set
      selection under a pause budget — G1's core idea in 200 lines. `[BUILD]` `[PROVE]`
4.4.8 Instrument all of the above with allocation rate, pause histogram, and throughput, then plot
      the throughput/pause/footprint triangle from your own numbers. `[BUILD]` `[NUM]`
4.4.9 Add reference objects: weak references cleared during marking, and a reference queue.
      `[BUILD]` `[PROVE]`
4.4.10 Diff vs the real one: safepoints and oop maps, precise stack scanning, parallelism and
       work-stealing termination, TLABs, PLABs, remembered-set data structures, humongous handling,
       evacuation failure, class unloading, string dedup, JNI roots, and the fact that real
       collectors must handle a mutator they do not control.

*(10 leaves)*

## §4.5 Memory-layout and footprint tools

4.5.1 `ObjectSizeCalculator` using `Instrumentation.getObjectSize` via a tiny agent — shallow size
      for any object. `[BUILD]`
4.5.2 A deep-size walker using reflection with an identity set to handle cycles and shared
      references, and the honest note that it double-counts nothing but cannot see native memory.
      `[BUILD]` `[PROVE]`
4.5.3 A layout printer that computes expected header + field + padding size from the class's
      declared fields, then compares it with JOL's actual output and explains the differences (field
      reordering, superclass gaps). `[BUILD]` `[NUM]` `[PROVE]`
4.5.4 A footprint comparison harness: `long[]` vs `Long[]` vs `List<Long>` vs `LongArrayList`, and
      `HashMap<Integer,Integer>` vs two parallel `int[]`s, measured with JOL and with
      Epsilon-GC-based allocation counting. `[BUILD]` `[NUM]` `[X-REF 02]`
4.5.5 A compressed-oops demonstration: run the same workload at `-Xmx30g` and `-Xmx33g` and measure
      the live-set difference. `[BUILD]` `[NUM]` `[PROVE]`
4.5.6 A compact-headers demonstration on Java 25: the same workload with and without
      `-XX:+UseCompactObjectHeaders`, reporting the live-set delta. `[BUILD]` `[NUM]`
      `[RESEARCH]`
4.5.7 Diff vs the real one: JOL's use of `Unsafe`/`VarHandle` offsets, its handling of hidden and
      array classes, and why `Instrumentation.getObjectSize` is an estimate by specification.

*(7 leaves)*

## §4.6 Failure reproducers

4.6.1 A **heap leak** reproducer: an unbounded `ConcurrentHashMap` cache in a singleton, driven by a
      load loop, run with a small heap and `HeapDumpOnOutOfMemoryError`. Then analyse your own dump
      in MAT to the root. `[BUILD]` `[PROVE]`
4.6.2 A **metaspace leak** reproducer: generate and load a class per iteration with ByteBuddy or
      `defineHiddenClass`, capped with `-XX:MaxMetaspaceSize=64m`. `[BUILD]`
4.6.3 A **direct buffer** leak reproducer: allocate direct buffers and hold them, capped with
      `-XX:MaxDirectMemorySize=64m`, then show `-XX:+DisableExplicitGC` making it worse. `[BUILD]`
      `[TRAP]`
4.6.4 A **thread leak** reproducer producing `unable to create new native thread`, and the
      `ulimit -u` interaction. `[BUILD]` `[X-REF 11]`
4.6.5 A **StackOverflowError** reproducer with mutual recursion, plus a measurement of maximum depth
      at three `-Xss` values. `[BUILD]` `[NUM]`
4.6.6 A **class-initialisation deadlock** reproducer, and the proof that `jstack`'s deadlock detector
      does not see it. `[BUILD]` `[PROVE]` `[TRAP]` `[X-REF 05]`
4.6.7 A **humongous allocation** reproducer: allocate arrays just over half a G1 region and watch
      old-gen grow with no leak, then fix it by raising `G1HeapRegionSize`. `[BUILD]` `[NUM]`
      `[PROVE]`
4.6.8 An **evacuation failure** reproducer: high allocation rate plus a large live set in a small
      heap, producing `to-space exhausted` in the log. `[BUILD]` `[DUMP]`
4.6.9 A **code cache exhaustion** reproducer with `-XX:ReservedCodeCacheSize=4m` and thousands of
      generated methods, demonstrating the silent throughput collapse. `[BUILD]` `[PROVE]`
      `[TRAP]`
4.6.10 A **long TTSP** reproducer: a counted loop with `-XX:-UseCountedLoopSafepoints`, measured
       with `-Xlog:safepoint`. `[BUILD]` `[NUM]` `[PROVE]`
4.6.11 A **deoptimisation storm** reproducer: a branch taken only after warmup, observed via
       `jdk.Deoptimization` JFR events. `[BUILD]` `[DUMP]`
4.6.12 A **fast-throw** reproducer: throw the same NPE in a hot loop until the stack trace
       disappears, then restore it with `-XX:-OmitStackTraceInFastThrow`. `[BUILD]` `[PROVE]`
       `[TRAP]`
4.6.13 An **OOMKill versus OutOfMemoryError** experiment in Docker: the same app with `-Xmx` at the
       limit versus at 70%, comparing exit 137 with a heap dump. `[BUILD]` `[X-REF 19]` `[PROVE]`
4.6.14 A **warmup** measurement harness: report per-request latency for the first 10 000 requests
        and plot the C1/C2 steps, then repeat with `-Xint`, `-XX:TieredStopAtLevel=1`, and an
        AppCDS archive. `[BUILD]` `[NUM]` `[PROVE]`

*(14 leaves)*

## §4.7 Diagnostic tooling you write yourself

4.7.1 A **GC log parser**: parse unified-logging young/mixed/full lines into records and compute
      allocation rate, promotion rate, pause percentiles, and the post-full-GC floor trend.
      `[BUILD]` `[NUM]`
4.7.2 A **thread dump classifier**: parse a `jstack` file, bucket threads by state and top frame, and
      emit "N BLOCKED on monitor X held by thread Y". `[BUILD]` `[PROVE]`
4.7.3 A **JFR post-processor** using `jdk.jfr.consumer.RecordingFile` to rank allocation sites,
      exception types and GC pauses from a `.jfr`. `[BUILD]`
4.7.4 A **`RecordingStream` watchdog** that logs a warning whenever a GC pause exceeds a threshold or
      a `jdk.VirtualThreadPinned` event fires. `[BUILD]` `[X-REF 05]`
4.7.5 A **custom JFR event** for a domain operation, with `@Category`, `@Threshold` and
      `shouldCommit()` used correctly. `[BUILD]`
4.7.6 A **memory-pressure watchdog** using `MemoryPoolMXBean.setCollectionUsageThreshold` plus a
      `NotificationListener` that triggers a heap dump via `HotSpotDiagnosticMXBean` — an automatic
      leak-evidence collector. `[BUILD]` `[PROVE]`
4.7.7 A **startup profiler**: a `premain` agent that timestamps every `ClassFileLoadHook` and prints
      the top classes by load time. `[BUILD]`
4.7.8 A **method-timing agent** with ByteBuddy, then measure its own overhead honestly and show the
      inlining it destroyed with `-XX:+PrintInlining`. `[BUILD]` `[PROVE]` `[TRAP]`
4.7.9 A **JMH suite** demonstrating: allocation cost, escape-analysis elimination, megamorphic
      dispatch cost, boxed vs primitive maps, and the volatile read/write asymmetry — each with
      `-prof gc` numbers. `[BUILD]` `[NUM]`
4.7.10 A **container sizing calculator**: given a memory limit, thread count, expected class count
       and buffer usage, output a recommended flag set and the residual headroom. `[BUILD]`
       `[NUM]`
4.7.11 Diff vs the real one: GCeasy/GCViewer's format coverage across JDK versions, JMC's rule
       engine, async-profiler's signal-based sampling, and why your agent is a teaching tool rather
       than a production one.

*(11 leaves)*

---

**PART 4 total: 7+8+9+10+7+14+11 = 66 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The questions, with the answer shape

Each leaf is one question plus the two-or-three-beat structure of a correct answer. The write pass
supplies the full answer; the syllabus fixes the question set.

**Architecture and memory areas**

5.1.1 Draw the JVM architecture: what are the runtime data areas and which are per-thread.
5.1.2 What is the difference between JDK, JRE and JVM — and where did the JRE go?
5.1.3 Heap versus stack: what lives where, and who can see it.
5.1.4 What is metaspace, what replaced, and why did PermGen fail?
5.1.5 Are static fields in metaspace? (No — the mirror `Class` on the heap.)
5.1.6 What is the code cache and what happens when it fills?
5.1.7 Why is `-Xmx` not the JVM's memory footprint? Enumerate every other term.
5.1.8 How big is a `java.lang.Object`? An `Integer`? A `new int[10]`? Show the arithmetic.
5.1.9 What is in an object header and what is the mark word used for?
5.1.10 What are compressed oops and what happens at 32 GB?
5.1.11 What are compact object headers and which release made them a product feature?
5.1.12 Where does a thread's stack live and what limits how many threads you can create?

**Class loading**

5.1.13 Walk the three phases of class loading with what happens in each.
5.1.14 What is parent-first delegation and what does it protect against?
5.1.15 What defines class identity in the JVM?
5.1.16 Explain `ClassCastException: com.acme.Order cannot be cast to com.acme.Order`.
5.1.17 `ClassNotFoundException` versus `NoClassDefFoundError` — which is which and why.
5.1.18 You see `NoClassDefFoundError` for a class that is definitely on the classpath. What
       happened?
5.1.19 What does `preparation` do to static fields, and when do initialisers actually run?
5.1.20 What triggers class initialisation, and what does *not*?
5.1.21 Why is the holder idiom thread-safe with no synchronization?
5.1.22 Can class initialisation deadlock, and would `jstack` show it?
5.1.23 What is a classloader leak, what pins the loader, and how do you find it?
5.1.24 When can a class be unloaded?
5.1.25 Why should you override `findClass` and not `loadClass`?
5.1.26 What is the context classloader for?
5.1.27 What is `UnsupportedClassVersionError` telling you, exactly?
5.1.28 What does the verifier check, and why can you no longer turn it off?

**Bytecode and execution**

5.1.29 Why is the JVM a stack machine?
5.1.30 Name the five invoke instructions and what each dispatches on.
5.1.31 How is a lambda compiled? Is it an anonymous class?
5.1.32 How does `String` concatenation compile in Java 8 versus Java 9+?
5.1.33 How does a `switch` on a `String` work at bytecode level?
5.1.34 Why does `byte b = b + 1;` not compile?
5.1.35 What is `invokedynamic` and name three features built on it.
5.1.36 What does `javac` optimise? (Almost nothing — say why.)
5.1.37 Why can a `static final int` change in one class and not in its callers?

**Garbage collection**

5.1.38 What is the generational hypothesis and what does it buy you?
5.1.39 Why is minor GC cheap? Derive it.
5.1.40 Walk an object from `new` to reclamation.
5.1.41 What are GC roots? List them.
5.1.42 Does GC collect cyclic garbage? Why does that follow from tracing?
5.1.43 Name every collector and give one line on when to choose it.
5.1.44 Which collector is the default, and since which release?
5.1.45 How does G1 work — regions, CSet, IHOP, mixed collections?
5.1.46 What is a humongous object and what problem does it cause?
5.1.47 What is "to-space exhausted" and what do you do about it?
5.1.48 How does ZGC get sub-millisecond pauses? What does it cost?
5.1.49 Why can't ZGC use compressed oops?
5.1.50 What changed in ZGC in Java 21 and again in 23/24?
5.1.51 Shenandoah versus ZGC — when would you pick each?
5.1.52 What is a write barrier and which collectors pay for one?
5.1.53 What is SATB and what problem does it solve?
5.1.54 What is a card table and how big is it?
5.1.55 What is a remembered set and why does a region-based collector need one?
5.1.56 What does `System.gc()` actually do?
5.1.57 What is a safepoint, and what is TTSP?
5.1.58 Why can a 10 ms GC pause actually be a 900 ms application pause?
5.1.59 What is a TLAB and why is Java allocation fast?
5.1.60 Is object pooling a good idea? When?
5.1.61 What is `GC overhead limit exceeded`?
5.1.62 How do you size a heap from first principles?
5.1.63 What is the single most useful number in a GC log?
5.1.64 What is string deduplication and how is it different from `intern()`?
5.1.65 Explain soft, weak and phantom references and when you would use each.
5.1.66 Why is `finalize` gone and what replaced it?
5.1.67 Why does a direct `ByteBuffer` leak native memory even when the heap is empty?

**JIT**

5.1.68 What is tiered compilation and what are the five levels?
5.1.69 After how many invocations does a method get compiled? (Trap — see §1.16.6.)
5.1.70 What is OSR and why do you need it?
5.1.71 What is deoptimisation and what triggers it?
5.1.72 What is escape analysis? Does it allocate objects on the stack?
5.1.73 What is an intrinsic? Name five.
5.1.74 What makes a call site monomorphic, and why do you care?
5.1.75 Does `final` on a method help the JIT?
5.1.76 What is inlining and what are the size thresholds?
5.1.77 Why does an APM agent slow down a service more than its own overhead suggests?
5.1.78 What is warmup, how do you measure it, and how do you deal with it in a deploy?
5.1.79 Why do you need JMH, and what does each of its features defend against?
5.1.80 Why is throwing exceptions in a hot loop expensive?
5.1.81 Why does an NPE in production sometimes have no stack trace?

**Diagnostics**

5.1.82 A service is at 100% CPU. Walk me through the diagnosis.
5.1.83 A service's memory grows until it is killed. Walk me through the diagnosis.
5.1.84 You have a heap dump. What do you look at first, and what is retained size?
5.1.85 What is the difference between OOMKilled and `OutOfMemoryError`?
5.1.86 What is exit code 137? 143?
5.1.87 Which flags do you always run with in production, and why each?
5.1.88 What does `jcmd` give you that `jstack`/`jmap` do not?
5.1.89 What is JFR, what does it cost, and what would you enable in production?
5.1.90 How do you find a native memory leak?
5.1.91 Why is RSS bigger than what NMT reports?
5.1.92 What is safepoint bias and why does async-profiler avoid it?
5.1.93 What do you do when the heap looks fine but latency is bad?
5.1.94 How do you diagnose a JVM that has already died?

**Containers and startup**

5.1.95 How does the JVM know it is in a container, and since when?
5.1.96 What is `MaxRAMPercentage`'s default and why is it wrong for you?
5.1.97 What happens with a 0.5-CPU limit, and what does it break?
5.1.98 How do you size a JVM for a 2 GB container? Show the arithmetic.
5.1.99 Why is CPU throttling worse than a small CPU count for a JVM?
5.1.100 What is CDS, what is AppCDS, and what is the AOT cache?
5.1.101 GraalVM native image versus HotSpot — what do you gain, what do you lose?
5.1.102 What is CRaC and when would you use it over native image?
5.1.103 Your liveness probe kills the pod during a GC pause. What is wrong?

**Staff-level / open-ended**

5.1.104 A service's p99 doubled after a deploy with no code change. Enumerate the JVM-level
        hypotheses in the order you would test them.
5.1.105 You must cut a fleet's memory cost by 30%. What are your levers, in order of
        risk-adjusted payoff?
5.1.106 Argue for and against moving a latency-sensitive service from G1 to ZGC.
5.1.107 How would you make a 40-second Spring Boot startup into 4 seconds? Enumerate every lever
        and its cost.
5.1.108 Design the JVM observability for a fleet of 500 services: what do you collect always, what
        on demand, and what do you page on?
5.1.109 A dependency upgrade caused metaspace to grow across redeploys. How do you prove which
        library, and what do you do about it?
5.1.110 Your service is fine at 100 rps and collapses at 130 rps with GC at 60% CPU. What is
        happening and what are the three fixes?

*(110 leaves)*

## §5.2 The trap index

One line per misconception, in the form *wrong belief → symptom → fix*. This is the pre-interview
review page, and every one of these must appear as a `**Trap:**` in the written guide.

5.2.1 "The heap is the JVM's memory."
5.2.2 "Set `-Xmx` to the container limit."
5.2.3 "`OutOfMemoryError` means the heap is full." (Read the text after the colon.)
5.2.4 "An `OutOfMemoryError` kills the JVM." (It kills one thread.)
5.2.5 "OOMKilled and `OutOfMemoryError` are the same thing."
5.2.6 "`System.gc()` frees memory."
5.2.7 "Minor GC doesn't pause the application."
5.2.8 "A bigger heap is always better."
5.2.9 "Serial GC is for toy applications."
5.2.10 "CMS is the low-pause collector." (Removed in 14.)
5.2.11 "ZGC is non-generational." (Default generational since 23.)
5.2.12 "ZGC is strictly better than G1."
5.2.13 "GC visits dead objects."
5.2.14 "GC pause time is the whole pause." (TTSP.)
5.2.15 "Object pooling reduces GC pressure."
5.2.16 "`finalize()` will clean it up."
5.2.17 "`SoftReference` is a cache."
5.2.18 "`WeakHashMap` prevents leaks." (Not if the value references the key.)
5.2.19 "Nulling a reference helps the GC." (Almost never; the JIT already knows.)
5.2.20 "The 32 GB heap is bigger than the 31 GB heap."
5.2.21 "Field declaration order is memory order."
5.2.22 "`Class` objects are in metaspace."
5.2.23 "Interned strings are in PermGen." (Heap since 7.)
5.2.24 "String deduplication is `intern()`."
5.2.25 "Metaspace is unlimited so I don't need to cap it."
5.2.26 "`-XX:MetaspaceSize` is the initial metaspace size." (It is the first GC threshold.)
5.2.27 "Class loading is eager."
5.2.28 "Two classes with the same name are the same type."
5.2.29 "`NoClassDefFoundError` means the class is missing."
5.2.30 "`Class.forName` and `loader.loadClass` are the same."
5.2.31 "Overriding `loadClass` is how you write a classloader."
5.2.32 "Redeploying is free."
5.2.33 "Reading a `static final` constant initialises the class."
5.2.34 "Interfaces are initialised when a subclass is."
5.2.35 "`jstack` finds all deadlocks." (Not class-init deadlocks.)
5.2.36 "A thread dump is free." (It is a safepoint.)
5.2.37 "`jstack` shows my virtual threads."
5.2.38 "Methods compile after 10 000 invocations." (Non-tiered only.)
5.2.39 "The JIT compiles everything eventually."
5.2.40 "Escape analysis allocates on the stack."
5.2.41 "`final` on a method helps the JIT."
5.2.42 "Microbenchmarks without JMH are fine."
5.2.43 "Warmup is a benchmark artifact, not a production concern."
5.2.44 "`-Xcomp` makes it fast."
5.2.45 "`-Xverify:none` speeds up startup." (Ignored since 18.)
5.2.46 "`-XX:+AggressiveOpts` / `-XX:+UseBiasedLocking` / `-XX:+UseConcMarkSweepGC` are still valid."
5.2.47 "An NPE always has a stack trace."
5.2.48 "Exceptions are cheap." (Construction is not.)
5.2.49 "A lambda is an anonymous class."
5.2.50 "`javac` optimises my code."
5.2.51 "`availableProcessors()` is the machine's core count."
5.2.52 "The JVM is container-aware, so defaults are fine." (25%.)
5.2.53 "RSS above NMT means a JVM bug."
5.2.54 "NMT tracks all native memory."
5.2.55 "The code cache filling throws an error." (It silently disables the JIT.)
5.2.56 "Direct buffers are freed when you drop the reference."
5.2.57 "`-XX:+DisableExplicitGC` is always safe." (It breaks direct-buffer reclamation.)
5.2.58 "GC logging is expensive."
5.2.59 "A heap dump is a cheap, safe operation."
5.2.60 "A JRE-only container image is fine for production." (No diagnostics.)
5.2.61 "Native image is just Java compiled to native." (SubstrateVM, closed world.)
5.2.62 "CDS/AOT works regardless of classpath changes."
5.2.63 "Biased → thin → fat lock escalation." (Biased locking is gone.)
5.2.64 "Metaspace leaks are heap leaks."

*(64 leaves)*

## §5.3 One-line assertions and drills

5.3.1 The assertion set that becomes the `## Atomic concept checklist` in the written guide — one
      flat line per distinct concept, covering every §1–§4 section. **Every existing checklist line
      in `src/topics/06-jvm-internals.md` must survive verbatim or expanded.**
5.3.2 The **numbers drill**: recite from memory — object header 12 B (compressed) / 16 B
      (uncompressed) / 8 B (compact), object alignment 8 B, array header 16 B, compressed-oops
      ceiling 32 GB, `MaxTenuringThreshold` 15 (4-bit age), card size 512 B, G1 target ~2048 regions
      sized 1–32 MB, `MaxGCPauseMillis` 200 ms, IHOP 45%, `G1NewSizePercent` 5 /
      `G1MaxNewSizePercent` 60, `G1HeapWastePercent` 5, `G1MixedGCLiveThresholdPercent` 85,
      `G1MixedGCCountTarget` 8, `NewRatio` 2, `SurvivorRatio` 8, `MaxRAMPercentage` 25%,
      `ReservedCodeCacheSize` 240 MB, `CompressedClassSpaceSize` 1 GB, `-Xss` ~1 MB,
      `GuaranteedSafepointInterval` 1000 ms, `SoftRefLRUPolicyMSPerMB` 1000,
      `TLABWasteTargetPercent` 1, `Tier3InvocationThreshold` 200 / `Tier3CompileThreshold` 2000 /
      `Tier4InvocationThreshold` 5000 / `Tier4CompileThreshold` 15000, `CompileThreshold` 10000
      (non-tiered), `MaxInlineSize` 35 / `FreqInlineSize` 325 / `MaxInlineLevel` 15,
      `StringTableSize` 65536, class file major = 44 + version (65 = Java 21), magic
      `0xCAFEBABE`, exit codes 137/143. `[NUM]`
5.3.3 The **table drill**: reproduce from memory the runtime-area table, the collector table, the
      OOM taxonomy table, the five compilation levels, the reference-strength table, and the
      class-loading phase table.
5.3.4 The **command drill**: write from memory, correctly, the command for — a thread dump, a heap
      dump, live GC stats, NMT summary and diff, starting a JFR recording, listing loaded
      classloaders, printing all final flag values, and changing GC logging at runtime. `[DUMP]`
5.3.5 The **diagnosis drill**: given a symptom (100% CPU / growing RSS / rising p99 / exit 137 /
      silent slowdown / process vanished), name the first three commands and what each would prove,
      in under sixty seconds. `[PROVE]`
5.3.6 The **log drill**: given a G1 log excerpt, a `jstat -gcutil` sample, an NMT summary and an
      `hs_err` header, state the diagnosis for each within thirty seconds. `[DUMP]`
5.3.7 The **arithmetic drill**: size a JVM for a 2 GB container; compute the live-set from a GC log;
      compute allocation rate from Eden size and GC frequency; compute the memory saved by compact
      headers on 50 M small objects. `[NUM]` `[PROVE]`
5.3.8 The **version drill**: for each of CMS, biased locking, PermGen, non-generational ZGC,
      compact headers, the AOT cache, `-Xverify:none` and `URLClassLoader`, state the release and
      the direction of the change. `[VERSION-TRAP]`
5.3.9 The **whiteboard drill**: draw the JVM architecture, the G1 heap with a marking cycle in
      progress, the object header bit layout, and the tiered-compilation state machine — each from
      memory in under three minutes.
5.3.10 Spaced-repetition plan: §5.2 daily, §5.1 architecture/GC/diagnostics weekly, PART 3 once
       before the onsite. Depth is read once; the trap index is read many times.
5.3.11 The two-minute answer template for any "the service is slow/dying" question: state the
       symptom class → state the first measurement → state what each outcome would rule out → state
       the fix and its cost → state the guardrail you would add so it cannot recur silently.

*(11 leaves)*

---

**PART 5 total: 110+64+11 = 185 leaves**

---

## Sources consulted

Primary sources are listed first within each group. Where a fetch failed or a search returned
nothing usable, that is stated rather than padded. Every `[RESEARCH]` leaf must be re-verified
against the source named here before the write pass commits a number to the page.

**Specification (primary)**

- <https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-5.html> — JVMS 21 chapter 5, fetched in
  full. Source of §1.4 (5.3.1–5.3.6 loading, array class creation, loading constraints, derivation,
  modules and layers), §1.5 (5.4.1 verification, 5.4.2 preparation and its loading constraints,
  5.4.3.1–5.4.3.6 resolution including the nine `REF_*` method-handle kinds and the seventeen
  resolution-triggering instructions, 5.4.4 access control and the nestmate algorithm, 5.4.5
  overriding, 5.4.6 selection, 5.6 native binding), and §1.6 (the 12-step initialisation procedure,
  the four class states, the `LC` lock, and the full error table).
- <https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html> — JVMS 21 chapter 4, the class
  file format: `ClassFile` structure, constant-pool tags, access flags, descriptors, and the
  attribute inventory. Basis of §1.2. Consulted via search summary plus the JVMS 5.0 chapter-4 PDF
  at <https://jcp.org/aboutJava/communityprocess/maintenance/jsr924/JVMS-SE5.0-Ch4-ClassFile.pdf>;
  **every tag number, flag value and limit in §1.2 must be re-read from the SE 21 text** during the
  write pass.
- <https://openjdk.org/jeps/8267650> — JEP draft "Better-defined JVM class file validation",
  confirming the format-check versus informational-assertion distinction used in §1.5.1–§1.5.2.

**JEPs and OpenJDK (primary)**

- <https://openjdk.org/jeps/312> — Thread-Local Handshakes: the per-thread polling-page indirection,
  the two always-guarded/always-unguarded pages, and the "stop one thread, not all" goal. Basis of
  §1.17.9 and §3.13.2.
- <https://openjdk.org/jeps/439> — Generational ZGC: colored pointers as state-encoding metadata,
  the load barrier's role, the **store barrier** added to move marking off the load path, and the
  distinct marking/relocation metadata bits per generation. Basis of §1.12.14, §3.8.10, §3.10.8.
- <https://openjdk.org/jeps/387> — Elastic Metaspace: per-classloader arenas, chunks, pointer-bump
  allocation within a chunk, the **buddy allocator** over root chunks, the class space as a confined
  region holding `Klass` structures with a 32-bit offset in the header, and the two commit limits
  (`MaxMetaspaceSize` and the GC threshold). Basis of §3.12.
- <https://openjdk.org/jeps/404> — Generational Shenandoah: the shared LRB across generations and
  the experimental status in JDK 24. Basis of §1.12.18.
- <https://openjdk.org/jeps/483> — Ahead-of-Time Class Loading & Linking: classes cached in a
  **loaded and linked** state, the training-run model, and the reported ~40% startup improvement.
  Basis of §1.18.16 and §3.16.6–§3.16.8.
- <https://openjdk.org/jeps/350> — Dynamic CDS Archives: `-XX:ArchiveClassesAtExit` layering on the
  default base archive. Basis of §1.18.15 and §3.16.5.
- <https://openjdk.org/jeps/454> and <https://openjdk.org/jeps/442> — the FFM API: `Linker`,
  downcalls and upcalls, `MemorySegment` backed by native or heap memory, and `Arena` as the
  off-heap lifetime manager. Basis of §3.15.7–§3.15.8.
- <https://openjdk.org/groups/hotspot/docs/RuntimeOverview.html> — the HotSpot runtime overview:
  the template interpreter generated at startup from `TemplateTable` via `InterpreterGenerator`, the
  dispatch table indexed by bytecode and interpreter state, and the runtime/compiler/memory-manager
  split. Basis of §3.1.1 and §3.2.1–§3.2.3. **A direct WebFetch of this URL returned HTTP 403**;
  the content came from the search summary and the mirrored discussions below, so §3.1–§3.2 carry
  `[RESEARCH]` and must be re-verified against the HotSpot source tree in the write pass.
- <https://wiki.openjdk.java.net/display/HotSpot/CompressedOops> — the three heap-placement
  strategies (below 4 GB → no base/no shift; below 32 GB → zero-based with shift; otherwise base +
  shift) and the 32 GB ceiling. Basis of §1.10.7–§1.10.9.
- <https://github.com/openjdk/jdk/blob/master/src/hotspot/share/oops/oop.hpp> — `oopDesc` holding a
  `volatile markWord _mark` and a `narrowKlass _compressed_klass`. Basis of §1.10.1–§1.10.2.
- <https://github.com/openjdk/jdk18/blob/master/src/hotspot/share/compiler/compilationPolicy.hpp>
  — the tiered compilation predicate
  `i > TierXInvocationThreshold * s || (i > TierXMinInvocationThreshold * s && i + b >
  TierXCompileThreshold * s)`. Basis of §1.16.4.

**JEPs fetched indirectly (403 on direct fetch)**

- <https://openjdk.org/jeps/450> (Compact Object Headers, experimental, JDK 24) and
  <https://openjdk.org/jeps/519> (product, JDK 25) both returned **HTTP 403** on direct fetch. The
  content — merging the mark word and the always-compressed class pointer into a single 64-bit
  header, the `-XX:+UseCompactObjectHeaders` flag, x64/AArch64 support, and the 10–20% live-set
  memory reduction — was taken from the OpenJDK mailing-list announcement
  <https://mail.openjdk.org/pipermail/jdk-dev/2024-October/009591.html>,
  <https://bugs.openjdk.org/browse/JDK-8294992>, <https://openjdk.org/jeps/534> (Compact Object
  Headers by Default), <https://nipafx.dev/inside-java-newscast-48/> and
  <https://www.baeldung.com/java-object-header-reduced-size-save-memory>. **Every bit-level layout
  claim in §1.10.6 and §3.18.2 must be re-verified against JEP 519 or the HotSpot source before
  writing.**

**GC documentation (primary)**

- <https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-g1-garbage-collector1.html> —
  fetched in full. Source of the G1 vocabulary (region, humongous ≥ half a region, SATB, remembered
  set, card table with **512-byte cards**, collection set, evacuation failure), the phase model
  (young-only: normal → Concurrent Start → Remark → Cleanup → Prepare Mixed; then space-reclamation
  mixed collections), the four pause sub-phases (Pre Evacuate, **Merge Heap Roots**, Evacuate, Post
  Evacuate), and the flag list `G1NewSizePercent`, `G1MaxNewSizePercent`,
  `InitiatingHeapOccupancyPercent`, `G1UseAdaptiveIHOP`, `G1HeapReservePercent`,
  `G1HeapRegionSize`, `G1HeapWastePercent`, `G1MixedGCCountTarget`, `G1PeriodicGCInterval`,
  `G1PeriodicGCInvokesConcurrent`, `G1PeriodicGCSystemLoadThreshold`,
  `G1EagerReclaimHumongousObjects`, `UseStringDeduplication`. Basis of §1.12.5–§1.12.11 and §3.9.
  **The page returned flag names but not every numeric default**; the defaults quoted in §1.12.6
  (200, 45, 5, 60, 5, 85, 8, 10) are from recall plus secondary sources and are tagged `[RESEARCH]`
  — re-verify with `java -XX:+PrintFlagsFinal -version` on a JDK 21 build.
- <https://www.oracle.com/technical-resources/articles/java/g1gc.html> and
  <https://docs.oracle.com/en/java/javase/22/gctuning/garbage-first-g1-garbage-collector1.html> —
  corroborating the humongous-object rule and the `G1HeapRegionSize` tuning advice for
  humongous-allocation-driven concurrent cycles. Basis of §2.2.7 and §3.9.11.
- <https://www.steveblackburn.org/pubs/papers/g1-vee-2020.pdf> ("Deconstructing the Garbage-First
  Collector") and <https://arxiv.org/pdf/2210.17175> — academic measurements of G1's barrier and
  remembered-set costs. Basis of §3.8.12 and §3.9.2, and the honest framing that barrier cost is a
  throughput number, not a pause number.
- <https://wiki.openjdk.org/spaces/zgc/pages/34668579/Main> and
  <https://wiki.openjdk.org/spaces/shenandoah/pages/25002018/Main> — the ZGC and Shenandoah project
  wikis for page sizes, cycle phases, heuristics and modes. Basis of §3.10 and §3.11.1–§3.11.5.
  **Both must be re-fetched in the write pass**; the ZGC coloured-pointer bit assignment in
  §3.10.1 is deliberately left unstated here because the layout changed with generational ZGC.

**JVM internals deep-dives**

- <https://shipilev.net/jvm/anatomy-quarks/> — fetched; the full 30-entry index was mined as a
  completeness checklist and directly produced leaves this syllabus would otherwise have missed:
  lock coarsening and loops (§3.5.13), transparent huge pages (§1.8.14), TLABs and **heap
  parsability** (§3.7.3), object initialisation costs (§3.7.5), JNI critical and the GC locker
  (§3.15.3), `String.intern()` (§3.19.6), moving GC and locality (§3.7.6), intergenerational
  barriers (§3.8), constant variables and just-in-time constants (§1.3.23, §3.4.10), megamorphic
  virtual calls (§3.3.6), trust non-static final fields (§3.4.10), scalar replacement (§3.5.6),
  lock elision (§3.5.13), heap uncommit (§1.12.26), safepoint polls (§3.13.1), compressed references
  (§1.10.7), object alignment (§1.9.18), **implicit null checks** (§3.4.8), identity hash code
  (§3.7.7), **compiler blackholes** (§2.7.6), frequency-based code layout (§3.6.8), and **uncommon
  traps** (§1.16.15). This single source is the largest contributor of `[RESEARCH]` leaves in
  PART 3.
- <https://shipilev.net/jvm/anatomy-quarks/4-tlab-allocation/>, <https://alidg.me/blog/2019/6/21/tlab-jvm>
  and <https://www.baeldung.com/java-jvm-tlab> — `TLABWasteTargetPercent` default **1**,
  `ResizeTLAB`, and the slow-path conditions. Basis of §2.5.4 and §3.7.2.
- <https://www.usenix.org/legacy/events/vee05/full_papers/p111-kotzmann.pdf> (Kotzmann & Mössenböck,
  "Escape Analysis in the Context of Dynamic Compilation and Deoptimization") — the escape states,
  scalar replacement of aggregates, and crucially the **reallocation and relocking of
  scalar-replaced objects on deoptimisation**. Basis of §3.5.4–§3.5.8.
- <https://cr.openjdk.org/~cslucas/escape-analysis/EscapeAnalysis.html> and
  <https://gist.github.com/navyxliu/62a510a5c6b0245164569745d758935b> (RFC: Partial Escape Analysis
  in HotSpot C2) — current EA status and the fact that **partial** EA is Graal, not C2. Basis of
  §1.16.19 and §3.5.7.
- <https://www.baeldung.com/jvm-tiered-compilation> and
  <https://epickrram.blogspot.com/2016/03/further-notes-on-hotspot-compiler-flags.html> —
  `Tier3InvocationThreshold=200`, `Tier3MinInvocationThreshold=100`, `Tier3CompileThreshold=2000`,
  `Tier4InvocationThreshold=5000`, and the non-tiered `CompileThreshold=10000`. Basis of §1.16.5.
  `Tier4MinInvocationThreshold=600` and `Tier4CompileThreshold=15000` are from recall and are
  tagged `[RESEARCH]`.
- <https://zackoverflow.dev/writing/template-interpreters/> — the template-interpreter technique and
  the dispatch-table mechanism in general. Basis of §3.2.2–§3.2.3.
- <https://jpbempel.github.io/2022/06/22/debug-non-safepoints.html> (via the concurrency syllabus's
  source set) — `-XX:+DebugNonSafepoints` and safepoint bias. Basis of §1.17.12–§1.17.13.
- <https://blanco.io/blog/jvm-safepoint-pauses/> and
  <https://foojay.io/today/the-inner-workings-of-safepoints/> — TTSP as distinct from pause
  duration, the polling-page trap mechanism, and `-Xlog:safepoint` reading. Basis of §1.17.3,
  §1.17.6 and §3.13.9.

**Memory, containers and native memory**

- <https://docs.oracle.com/en/java/javase/23/vm/native-memory-tracking.html> — NMT levels
  (`off`/`summary`/`detail`), `jcmd VM.native_memory baseline` and `summary.diff`, and the explicit
  statement that NMT **does not track third-party native code or all JDK class-library
  allocations**. Basis of §2.12.2–§2.12.4.
- <https://medium.com/@itshimanshusingh/why-rss-is-bigger-than-nmt-profiling-java-native-memory-in-production-3615a2e00d46>
  and <https://blog.rohlik.group/blog/taming-jvm-memory-jdk25-part2> — a measured 527–537 MB gap
  between RSS and NMT-committed attributed to glibc per-arena free lists and tcache plus mapped
  shared libraries. Basis of §2.12.5 and §1.14.20. **These are secondary sources; the numbers are
  presented as an order of magnitude, not as constants.**
- <https://poonamparhar.github.io/troubleshooting_native_memory_leaks/> and
  <https://krzysztofslusarski.github.io/2025/03/31/native.html> — jemalloc/`jeprof` profiling,
  `pmap -X`, and the `Inflater`/`Deflater` and `ZipFile` leak classes. Basis of §2.12.6–§2.12.8.
- <https://docs.oracle.com/en/java/javase/21/vm/class-data-sharing.html> — the default CDS archive
  shipped since JDK 12 and enabled at runtime, dynamic archive creation layered on it, and
  `-XX:+RecordDynamicDumpInfo` as the JDK 21 alternative to `-XX:ArchiveClassesAtExit`. Basis of
  §1.18.14–§1.18.15 and §3.16.5.

**Tooling**

- <https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html> — the authoritative JDK 21
  jcmd command list, which supplied §1.20.3 verbatim including the commands most guides omit
  (`VM.classloaders`, `VM.classloader_stats`, `VM.class_hierarchy`, `VM.metaspace`,
  `VM.stringtable`, `VM.symboltable`, `VM.systemdictionary`, `Compiler.CodeHeap_Analytics`,
  `System.native_heap_info`, `System.trim_native_heap`, `GC.finalizer_info`, `GC.class_stats`).
- <https://github.com/async-profiler/async-profiler/blob/master/docs/ProfilerOptions.md> — the event
  list (`cpu`, `alloc`, `lock`, `wall`, `itimer`, `ctimer`), `AsyncGetCallTrace` plus POSIX signals
  as the no-safepoint-bias mechanism, `perf_events` for native frames, and JFR as the only
  multi-event output format. Basis of §1.20.17 and §2.10.9.
- <https://bugs.openjdk.org/browse/JDK-8257602> ("Introduce JFR Event Throttling and new
  jdk.ObjectAllocationSample event") and <https://jbachorik.github.io/posts/jfr-allocation-profiling>
  — the JDK 16 allocation-sampling redesign and the throttle defaults of **150 samples/s (default
  template)** and **300 samples/s (profile template)**. Basis of §1.20.13 and §2.11.3.
- <https://inside.java/2022/04/25/sip48/> — custom JFR events (`extends jdk.jfr.Event`, `@Name`,
  `@Label`, `@Category`, `begin`/`commit`/`shouldCommit`). Basis of §1.20.14 and §4.7.5.
- <https://blog.ycrash.io/jvm-production-troubleshooting-guide/>,
  <https://blog.heaphero.io/java-classloader-leaks/> and
  <https://ops.java/performance/jvm/articles/long-gc-pauses/> — the leak sawtooth signature, the
  back-to-back-full-GC metaspace signature, and the classloader-leak root list. Basis of §2.9.1,
  §2.9.9 and §1.7.13–§1.7.15.
- <https://krzysztofslusarski.github.io/2020/11/29/g1outage.html> and
  <https://krzysztofslusarski.github.io/2021/08/10/monday-phases.html> — reading G1 unified-logging
  phases, `to-space exhausted`, and the `User`/`Sys`/`Real` line as a CPU-starvation detector.
  Basis of §2.3.7–§2.3.10.

**Startup and alternative runtimes**

- <https://inside.java/2025/06/29/javaone-leyden-aot/> and
  <https://www.baeldung.com/java-aot-class-loading-linking> — the Leyden AOT cache workflow, and
  JEP 514/515 (one-step ergonomics and AOT method profiling) as the JDK 25 follow-ons. Basis of
  §1.18.16, §2.8.6 and §3.16.7–§3.16.8.
- <https://www.javacodegeeks.com/2025/12/graalvm-native-image-vs-traditional-jvm-understanding-the-trade-offs.html>
  and <https://www.javacodegeeks.com/2026/04/graalvm-native-image-vs-project-leyden-two-answers-to-the-same-cold-start-problem.html>
  — closed-world assumption, the reflection/proxy/serialization configuration requirement, and
  measured startup/RSS/peak-throughput deltas. **These are secondary and vendor-adjacent; the
  numbers in §1.18.17 and §2.8.12 must be presented as "reported" with the source named, not as
  facts, or replaced by the reader's own measurement.** `[RESEARCH]`
- <https://www.oracle.com/java/technologies/javase/25-relnote-issues.html> and
  <https://inside.java/2025/10/20/jdk-25-performance-improvements/> — the JDK 25 change list used to
  build §2.15.16.

**Curriculum / completeness probes**

- <https://ptgmedia.pearsoncmg.com/images/9780137142521/samplepages/0137142528.pdf> and the
  *Java Performance* (Hunt & John) table of contents — used purely as a coverage checklist. It
  contributed the "OS-level monitoring before JVM-level monitoring" framing (§2.10.12, §2.4.7), the
  explicit "HotSpot VM Runtime / GC / JIT / adaptive tuning" decomposition adopted in §3.1.1, and
  the reminder that a JVM performance curriculum starts with a *methodology* section, which became
  §2.2.2.
- <https://blog.gceasy.io/3-popular-myths-about-garbage-collection/> and
  <https://medium.com/@ujjawalr/7-jvm-myths-backend-developers-still-believe> — mined for the trap
  index: "minor GC doesn't pause", "Serial GC is a toy", "GC collects dead objects" (it tracks live
  ones), and the tuning-mistake list. Basis of §2.2.10–§2.2.13 and several §5.2 entries.
- <https://www.baeldung.com/java-memory-management-interview-questions>,
  <https://www.theserverside.com/feature/Java-garbage-collection-interview-questions-and-answers>,
  <https://www.java67.com/2020/02/50-garbage-collection-interview-questions-answers-java.html> and
  <https://blog.ycrash.io/java-garbage-collection-interview-questions/> — mined only for question
  names not already in §5.1. They contributed the staff-level operational questions
  (§5.1.104–§5.1.110): JIT warmup during autoscaling, why allocation rate matters more than heap
  size, why a full GC is a high-priority incident, and how classloader leaks present in production.

**Not found / not usable**

- Direct fetches of <https://openjdk.org/jeps/450>, <https://openjdk.org/jeps/519> and
  <https://openjdk.org/groups/hotspot/docs/RuntimeOverview.html> all returned **HTTP 403**. Every
  constant derived from them carries `[RESEARCH]` and must be re-verified from the HotSpot source
  tree, the JDK release notes, or `-XX:+PrintFlagsFinal` output before the write pass states it.
- No primary source was found for an authoritative, current per-operation cost table (allocation
  fast path, safepoint entry, JNI transition). The numbers in §2.1.2, §3.7.1 and §3.15.2 are
  order-of-magnitude and **must be presented as such**, ideally alongside a JMH harness the reader
  can run (§4.7.9) rather than as quoted constants.
- No source was found giving the current ZGC coloured-pointer bit assignment for **generational**
  ZGC; §3.10.1 therefore instructs the write pass to read it from
  `src/hotspot/share/gc/z/zAddress.hpp` rather than quoting a pre-JDK-21 layout.
- Searches for published *university course* syllabi on JVM internals returned nothing usable
  beyond book tables of contents; the curriculum angle was covered by the *Java Performance* TOC
  instead.

## Gaps vs the current guide

`src/topics/06-jvm-internals.md` is **323 lines** across 7 sections plus a 25-item checklist. It is
a competent operations-focused summary and a poor bible: it has no class file format, no bytecode,
no linking/initialization, no object layout, no collector internals, no JIT internals, no
safepoints, no startup story, and no build-it content at all. The table below is the work order —
every row marked *missing* is content the bible must add, every row marked *shallow* exists but at
one to three lines where the syllabus demands mechanism, numbers or proof.

| Syllabus area | Present in `src/topics/06-jvm-internals.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why a VM exists, JDK/JRE/JVM, the pipeline | — | ✅ entire section | |
| §1.2 the class file format | — | ✅ entire section (magic, versions, constant pool, descriptors, attributes, the 64K limits) | |
| §1.3 bytecode and the execution model | — | ✅ entire section (frames, the five invokes, `invokedynamic`, lambdas, switch, `javap`) | |
| §1.4 class loading (JVMS 5.3) | §4 (28 lines) | ✅ defining vs initiating loader, loading constraints, run-time packages, array classes, modules/layers, `ClassLoader` API, parallel-capable loaders, the full `LinkageError` family, `ServiceLoader`, context classloader | ✅ delegation and identity are one line each |
| §1.5 linking (JVMS 5.4) | §4 (one clause: "verification, preparation, resolution") | ✅ the whole of verification, `StackMapTable`, preparation semantics, all six resolution kinds, access control and nestmates, overriding vs selection, binary compatibility | ✅ severely |
| §1.6 initialization and `LC` | §4 (one clause) | ✅ the 12-step procedure, the five triggers and the non-triggers, the erroneous state, class-init deadlock, circular init reading defaults, `<clinit>` cost | ✅ severely |
| §1.7 the loader hierarchy in practice | §4 | ✅ the Java 9 change and the `URLClassLoader` break, parent-last, class unloading rules, hidden classes, hot reload, Spring Boot's loader, `-Xlog:class+load` | ✅ the leak list exists but without detection or prevention |
| §1.8 runtime data areas | §1 (table + 3 paragraphs) | ✅ JVMS-vs-HotSpot split, frame anatomy, stack depth numbers, the run-time constant pool, string/symbol tables, per-thread native structures, the full footprint equation | ✅ the table is good; everything under it is one line |
| §1.9 heap, allocation, generational model | §2 (11 lines) | ✅ TLAB, the three allocation paths, zeroing, GC roots enumerated, reachability, tenuring flags, `NewRatio`/`SurvivorRatio`, premature promotion, allocation rate and live set as metrics, object alignment, footprint arithmetic, JOL | ✅ |
| §1.10 object layout, headers, oops/klass | — | ✅ entire section (mark word, compressed oops and the 32 GB cliff, compact headers, field layout, `Klass`/vtable/itable, array layout) | |
| §1.11 GC model and vocabulary | §2 | ✅ tri-colour, the lost-object problem, SATB vs incremental update, barriers, card table, remembered sets, CSet, evacuation failure, floating garbage, GC thread counts, ergonomics, the pause budget as an SLO input | ✅ |
| §1.12 the collectors | §2 (table + 3 paragraphs) | ✅ CMS removal, Serial's legitimate uses, Parallel's flags, G1's full flag surface and phase model, ZGC generational and its version history, Shenandoah, Epsilon, string dedup vs intern vs compact strings, heap uncommit | ✅ G1 and ZGC get one paragraph each |
| §1.13 references, finalization, `Cleaner` | §2 (one **Trap:** line) | ✅ the four strengths and their rules, `SoftRefLRUPolicyMSPerMB`, `WeakHashMap`, reference processing as a pause, finalization's three failure modes, `Cleaner`'s capture rule, the `DisableExplicitGC`/direct-buffer interaction | ✅ severely |
| §1.14 memory outside the heap | §1 (table row) + §7 | ✅ metaspace internals and flags, the code cache and its **silent** failure, segmented code cache, direct memory and the per-thread buffer cache, mapped files, GC structures, NMT categories, glibc arenas | ✅ |
| §1.15 the failure taxonomy | §3 (table + 2 paragraphs) | ✅ `Out of swap space?`, compressed class space, the `CrashOnOutOfMemoryError` family, **the `hs_err` file**, `ErrorFile`, SIGSEGV triage, the failure decision tree | ✅ the OOM table is good and must be preserved verbatim |
| §1.16 JIT | §5 (23 lines) | ✅ the five levels, the trigger predicate and every threshold, OSR, compiler threads, the optimisation inventory, inlining budgets, mono/bi/megamorphic, uncommon traps, deopt storms, intrinsics, `PrintInlining`/`CompileCommand` | ✅ tiers and warmup are one paragraph each; JMH block must be preserved and expanded |
| §1.17 safepoints and handshakes | — | ✅ entire section — and it is the missing half of every GC-pause conversation | |
| §1.18 startup, shutdown, flags | §5 (one clause on CDS) | ✅ the startup sequence, ergonomics, flag categories, the env-var injection traps, a defended baseline flag set, the anti-flag list, shutdown hooks, CDS/AppCDS/AOT cache/CRaC/native image, `jlink` | ✅ |
| §1.19 the memory model at implementation level | — | ✅ entire section (barriers emitted, x86 vs AArch64, the JIT as a reordering source, the class-init lock, monitor implementation pointer) | |
| §1.20 the diagnostic toolchain | §6 (table + 2 workflows) | ✅ the full jcmd inventory, JSON thread dumps, `jhsdb`, the `jfr` CLI, the JFR event inventory, custom events, JMC, async-profiler, flame-graph reading, MXBeans, the container attach traps | ✅ the tool table is good and must be preserved; JFR gets one line |
| PART 2 — the master tables | — | ✅ all eight | |
| PART 2 — GC tuning as a procedure | §2 (3 lines of advice) | ✅ the measurement order, sizing derivations, per-collector playbooks, the five mistakes, the three myths | ✅ |
| PART 2 — reading GC logs | §2 (one log line) | ✅ the `-Xlog` grammar, cause vocabulary, phase breakdown, `User/Sys/Real`, computing rates by hand, the three signatures | ✅ |
| PART 2 — container sizing | §7 (24 lines) | ✅ cgroup verification, the sizing worksheet, CPU throttling vs CPU count, probes, heap dumps in containers, base-image diagnostics | ✅ good on `MaxRAMPercentage` and OOMKilled; both must be preserved |
| PART 2 — allocation economics | — | ✅ entire section | |
| PART 2 — class loading in practice, agents | §4 | ✅ startup budget, jar-hell diagnosis, agents and their cost, redefinition limits, reflection cost, the prevention checklist | ✅ |
| PART 2 — JIT in practice and JMH | §5 | ✅ warmup measurement, canary/ramp reasoning, the full JMH surface, blackholes, `-prof`, the `final` myth | ✅ the JMH snippet must be preserved and expanded |
| PART 2 — startup engineering | — | ✅ entire section | |
| PART 2 — heap dumps and leak hunting | §6 (workflow, 5 steps + culprit list) | ✅ dominator-tree theory, dump costs and flags, large-dump handling, `jdk.OldObjectSample`, native-vs-heap triage, regression prevention | ✅ the workflow and the culprit list are the guide's best content and must be preserved verbatim and extended |
| PART 2 — thread dumps and CPU | §6 (workflow) | ✅ dump anatomy, the pattern catalogue, what the deadlock detector misses, virtual threads, async-profiler event choice, "slow but not busy" | ✅ the `top -H` workflow must be preserved verbatim |
| PART 2 — JFR in production | §6 (one table row) | ✅ entire section | ✅ |
| PART 2 — native memory and the RSS gap | §7 (NMT mentioned) | ✅ the diagnosis order, NMT's blind spots, jemalloc profiling, the specific native leak classes, FFM arenas | ✅ |
| PART 2 — JVM observability surface | — | ✅ entire section (MXBeans, Micrometer metric names, the four alerts, JMX in Kubernetes) | |
| PART 2 — choosing a runtime | — | ✅ entire section | |
| PART 2 — version delta 8 → 25 | — | ✅ entire section — and it is the highest-value single addition, because most of this topic's folklore is version-stale | |
| PART 3 — HotSpot skeleton, source map, `globals.hpp` | — | ✅ | |
| PART 3 — the template interpreter | — | ✅ | |
| PART 3 — dispatch, inline caches, vtables, CHA | — | ✅ | |
| PART 3 — C1/C2 internals, sea of nodes, RCE, implicit null checks | — | ✅ | |
| PART 3 — inlining, EA, deoptimisation in depth | §5 (one sentence on escape analysis) | ✅ | ✅ |
| PART 3 — the code cache lifecycle, oop maps, dependencies | — | ✅ | |
| PART 3 — allocation internals and heap parsability | — | ✅ | |
| PART 3 — GC barriers, all collectors | — | ✅ | |
| PART 3 — G1 internals | §2 (one paragraph) | ✅ | ✅ |
| PART 3 — ZGC internals | §2 (three lines) | ✅ | ✅ |
| PART 3 — Shenandoah / Parallel / Serial / Epsilon / CMS history | §2 (table rows) | ✅ | ✅ |
| PART 3 — metaspace internals (buddy allocator, class space) | §1 (one paragraph) | ✅ | ✅ |
| PART 3 — safepoint internals | — | ✅ | |
| PART 3 — exception handling, fast-throw, `StackWalker` | — | ✅ — and the missing-stack-trace trap is a real production symptom the guide never mentions | |
| PART 3 — JNI, FFM, native interop | — | ✅ | |
| PART 3 — CDS/AOT/Leyden/native-image internals | §5 (one clause) | ✅ | ✅ |
| PART 3 — JVMTI and agents | — | ✅ | |
| PART 3 — the JVM's own concurrency machinery, continuations | — | ✅ | |
| PART 3 — reference processing and string internals | — | ✅ | |
| PART 3 — HPROF and thread-dump formats | — | ✅ | |
| PART 3 — unified logging and `hs_err` internals | §2 (one log flag) | ✅ | ✅ |
| PART 4 — every `[BUILD]` (§4.1–§4.7) | — | ✅ all 66 leaves; the current guide contains no implementable content whatsoever | |
| PART 5 — the 110-question set | — | ✅ | |
| PART 5 — the 64-item trap index | 6 `**Trap:**` markers inline | ✅ all six must be preserved and 58 added | |
| PART 5 — numbers/table/command/diagnosis/log/arithmetic/version/whiteboard drills | closing checklist (25 lines) | ✅ the drills | ✅ the checklist must be preserved verbatim and extended |

Two corrections the write pass **must** make to existing text, not merely additions:

1. §5 of the current guide says AOT/CDS is "`-XX:SharedArchiveFile`" and stops there. In Java 21
   that is CDS only; Java 24/25 add the Leyden AOT cache (`-XX:AOTCache`, `-XX:AOTCacheOutput`)
   which caches **loaded and linked** classes plus method profiles. State the version boundary
   explicitly rather than leaving CDS as "the" answer.
2. §2 of the current guide describes ZGC as "concurrent … using coloured pointers and load
   barriers" with no mention of generations. Since Java 21 ZGC is generational (opt-in), since
   Java 23 generational is the default, and since Java 24 the non-generational mode is **removed**;
   the generational design also adds a **store barrier**. The current text is a pre-21 description
   and reads as stale.

Six passages in the current guide are strong and must survive **verbatim or expanded**, not
rewritten: the runtime-area table (§1), the OOM taxonomy table (§3), the `CNFE`-vs-`NoClassDefFoundError`
trap (§4), the `top -H` 100%-CPU workflow (§6), the MAT leak workflow with its culprit list (§6),
and the OOMKilled-versus-`OutOfMemoryError` trap (§7).

---

## Footer — leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.20 | 420 |
| PART 2 — Intermediate | §2.1–§2.15 | 195 |
| PART 3 — Under the hood | §3.1–§3.21 | 222 |
| PART 4 — Build it | §4.1–§4.7 | 66 |
| PART 5 — Interview and retention | §5.1–§5.3 | 185 |
| **Total** | **66 sections** | **1088 leaves** |

`[RESEARCH]`-tagged leaves: **231** (PART 1: 96, PART 2: 51, PART 3: 76, PART 4: 3, PART 5: 5).
Each must be re-verified against its cited source during the write pass before any constant from it
is written down. The highest-risk clusters are: every G1 flag default in §1.12.6 (the Oracle page
gave names, not all numbers), the compact-header bit layout in §1.10.6 (JEP fetch returned 403),
the ZGC coloured-pointer layout in §3.10.1 (deliberately unstated here), the tier-4 thresholds in
§1.16.5, and every "reported" startup/throughput percentage in §1.18.17 and §2.8.12.

Target version restated for the write pass: **Java 21 LTS on 64-bit HotSpot**, with every Java
22–25 divergence marked `[VERSION-TRAP]` inline. The four deltas that most often produce a stale
answer are **generational ZGC (default in 23, non-generational removed in 24)**, **compact object
headers (experimental 24, product 25)**, **the Leyden AOT cache (24/25) superseding CDS as the
startup answer**, and **CMS and biased locking being gone** (14 and 18 respectively) from answers
that still cite them.






</content>
</invoke>
