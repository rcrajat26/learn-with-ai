# 04 Modern Java — The platform and the release model — INTERNALS (§3.16)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [The platform and the release model — migration](02-migration.md) · Next: [The platform and the release model — internals observability](04-internals-observability.md)

## The shape of the timeline

Six-month cadence since Java 9 (September/March), an LTS every roughly three years, and every
language feature — since JEP 12 formalized it after Java 9 — goes through one or more **preview**
releases before it is allowed to become permanent. The table below is the map; the rest of this
file is the streets.

| Release | Date | LTS? | Headline mechanism-level features |
|---|---|---|---|
| 8 | 2014-03 | LTS | lambdas, streams, `Optional`, PermGen → Metaspace |
| 9 | 2017-09 | — | JPMS, immutable collection factories, `Flow` |
| 10 | 2018-03 | — | `var`, AppCDS |
| 11 | 2018-09 | LTS | `HttpClient`, ZGC (exp.), Java EE removed |
| 12 | 2019-03 | — | `teeing`, switch expr. (preview 1) |
| 13 | 2019-09 | — | text blocks (preview 1), switch expr. (preview 2) |
| 14 | 2020-03 | — | switch expr. final, records (preview 1) |
| 15 | 2020-09 | — | text blocks final, sealed (preview 1) |
| 16 | 2021-03 | — | records final, `instanceof` pattern final |
| 17 | 2021-09 | LTS | sealed final, pattern switch (preview 1) |
| 18 | 2022-03 | — | UTF-8 default, simple web server |
| 19 | 2022-09 | — | virtual threads (preview 1), record patterns (preview 1) |
| 20 | 2023-03 | — | all four re-previewed, scoped values (incubator) |
| 21 | 2023-09 | LTS | virtual threads final, pattern matching for switch final |
| 22 | 2024-03 | — | unnamed variables final, FFM final |
| 23 | 2024-09 | — | string templates withdrawn, Markdown javadoc |
| 24 | 2025-03 | — | gatherers final, `synchronized` no longer pins |
| 25 | 2025-09 | LTS | scoped values final, compact source files final |

**Insight:** the preview mechanism is not a marketing label. A preview feature ships in the real
javac and the real JVM, compiled classes are tagged with a minor version that only a JVM run with
`--enable-preview` will load, and the feature can still change shape or be withdrawn between
previews — string templates did exactly that between Java 21 and Java 23. Treat "preview" the way
you treat a database migration behind a feature flag: real code, explicitly gated, reversible.

---

## Primary concept: the preview-feature lifecycle mechanism

**Mental model.** A preview feature is not "beta" in the informal sense — it is a fully
implemented language or API change with one bit flipped in the class file. `javac
--release 21 --enable-preview` stamps the compiled `.class` file's minor version field
(normally `0x0000`) with `0xFFFF`, the JVM's dedicated "this class used preview features"
marker. `java --enable-preview` is the only way to load such a class; without the flag, the
JVM refuses it with `UnsupportedClassVersionError` naming the specific preview requirement.

**Why it exists.** Before JEP 12 formalized the process (Java 9 era, first fully exercised at
scale from Java 12), a language feature either shipped as final in one release or lived years in
a separate experimental branch (Project Amber's early sealed-types work, or the pre-2004 generics
debates) with no way for ordinary users to compile against it and give feedback that could still
change the design. Previewing in the mainline compiler means real production code — gated behind
a flag nobody ships to prod with — can exercise the feature and its edge cases before the design
locks.

**When to reach for it, and when not.** Never ship a preview feature to a customer-facing
production JAR: the flag must travel with the classfile forever (a `--enable-preview`-compiled
class from Java 21 will not run un-flagged on Java 22 without recompiling, because the preview
minor-version tag is specific to the JDK feature version that produced it). Reach for a preview
feature in a spike, a proof of concept for an internal proposal, or CI experiments comparing two
designs — never in `main`.

**How it works.** Three JDK-wide levers gate a preview feature, applied identically regardless of
which JEP:

1. `javac --release N --enable-preview` — compiles the syntax/API and stamps the class file.
2. `java --enable-preview` — required to load a stamped class; every `.class` on the runtime
   classpath produced with the flag needs it.
3. `--source N --enable-preview` at the `jshell`/single-file-launch level, for scripts that skip
   an explicit `javac` step (Java 11's single-file source launcher, generalized by Java 22).

A preview feature can be **re-previewed** (its second, third, … round, syntax possibly changed —
structured concurrency ran five rounds, JEP 428 through JEP 505), **finalized** (the flag drops
forever, e.g. records at Java 16), or **withdrawn** (string templates, JEP 430, pulled after
Java 21's preview when review concluded string interpolation and multi-line templating deserved a
different design — nothing shipped in Java 22 or 23 in its place, and the redesign is still in
flight per 3.16.19).

**Example.** QuizStakes' settlement path fans out `ReserveStake` / `SettleStake` calls to the
Quiz Engine and the PSP concurrently; the Java 21 preview shape for that is `StructuredTaskScope`,
which needs the flag on both ends:

```java
import java.util.concurrent.StructuredTaskScope;
import java.util.concurrent.StructuredTaskScope.ShutdownOnFailure;

// javac --release 21 --enable-preview Settlement.java
// java  --release 21 --enable-preview Settlement
final class StakeSettlementCoordinator {

    Movement settle(RoundId roundId, Money stake) throws InterruptedException {
        try (var scope = new ShutdownOnFailure()) {
            var quizEngineCall = scope.fork(() -> settleAgainstQuizEngine(roundId, stake));
            var ledgerCall = scope.fork(() -> reserveLedgerEntry(roundId, stake));
            scope.join();
            scope.throwIfFailed(RuntimeException::new);
            return new Movement(quizEngineCall.get(), ledgerCall.get());
        }
    }

    private String settleAgainstQuizEngine(RoundId roundId, Money stake) { return "SETTLED"; }
    private String reserveLedgerEntry(RoundId roundId, Money stake) { return "CLIENT_BONUS_RESERVED"; }
}
```

**Pitfall:** a class compiled with `--enable-preview` on Java 21 does not run on Java 22 even with
`--enable-preview` supplied again — the preview marker is tied to the exact feature version that
produced it, so upgrading the JDK for an app still using a preview API means recompiling against
the new JDK, not just relaunching.

**Interview:** "why does Java preview features instead of shipping them straight to final?" —
because a language change is effectively permanent once real code depends on it; previewing buys
one to five releases of real-world feedback (structured concurrency needed five) while keeping the
door open to change the shape, at the cost of the feature being unusable in production until it
finalizes.

> **Definition:** a preview feature is a complete, compiler- and JVM-enforced implementation of a
> not-yet-permanent Java feature, usable only with `--enable-preview` on both compilation and
> execution, that may be re-previewed, changed, finalized, or withdrawn before it becomes ordinary
> Java.

---

## Java 8 through Java 25, release by release

### Java 8 (2014) — §3.16.1

Lambdas, method references and functional interfaces are the mechanism this whole platform era
runs on — invokedynamic-backed call sites generated by `LambdaMetafactory`, not anonymous-class
desugaring. **[X-REF 03]** That bytecode mechanism, `invokedynamic`'s bootstrap, and the
functional-interface contract (`@FunctionalInterface`, single abstract method) are guide 03's
territory in full; the load-bearing fact for this file is that a lambda expression compiles to a
private synthetic method plus one `invokedynamic` call site, generated once per lambda shape and
linked lazily on first execution — which is why the first call through a given lambda site is
slower than the rest.

Streams, `Optional`, default and static interface methods, `java.time`, `CompletableFuture`,
`StringJoiner`, `Base64`, `Arrays.parallelSort`, repeating and type annotations all landed the
same release; each is a supporting fact for this file's purposes and gets its full mechanism
treatment in guide 03 (streams, `Optional`, `CompletableFuture`) or guide 05 (the concurrency half
of `CompletableFuture`).

PermGen's replacement by Metaspace is the one JVM-level change in this list. **[X-REF 06]**
Mechanically: class metadata moved out of the heap-adjacent, fixed-size PermGen into
native-memory Metaspace, sized by `-XX:MetaspaceSize` / `-XX:MaxMetaspaceSize` rather than
`-XX:MaxPermSize`, which is why `OutOfMemoryError: PermGen space` from a classloader leak became
`OutOfMemoryError: Metaspace` from Java 8 onward — same underlying leak (classes retained by a
live classloader that should have been collected), different ceiling and different flag. The full
class-metadata layout and classloader-unloading conditions are guide 06's territory.

Nashorn (the JavaScript engine) shipped in 8 and is relevant here only because it was removed in
15 (§3.16.8) — noted at that point, not here.

### Java 9 — §3.16.2

JPMS (the module system: `module-info.java`, `requires`/`exports`, strong encapsulation of JDK
internals) is the release's structural change; guide 06 covers classloader and layer mechanics.
`List.of` / `Set.of` / `Map.of` return genuinely immutable, not merely unmodifiable, backing
structures — `UnsupportedOperationException` on any mutator, and (unlike `Collections
.unmodifiableList`) no live view of a mutable backing collection to leak through. `Optional
.stream()` lets a `Stream<Optional<T>>` flatten via `.flatMap(Optional::stream)` instead of a
filter-then-map pair; `Optional.or(Supplier)` chains a fallback `Optional` without unwrapping;
`ifPresentOrElse` gives the else-branch that Java 8's `Optional` conspicuously lacked.
`Stream.takeWhile` / `dropWhile` are short-circuiting on **ordered** streams only — on an unordered
stream `takeWhile` is not guaranteed to stop at the first non-matching element, since "first" is
undefined. `Stream.iterate(seed, hasNext, next)` (the three-argument overload) added a
termination predicate so `iterate` no longer required an artificial `.limit()` to avoid an
infinite stream. Private interface methods let two default methods share code without exposing
it. JShell, `jlink` (custom minimal runtimes), `Flow` (the `java.util.concurrent.Flow`
reactive-streams interfaces — mechanics are guide 05's), `VarHandle` (a `sun.misc.Unsafe`
replacement for fenced field access — guide 06), `StackWalker` (a lazy, filterable alternative to
`Thread.getStackTrace()` that avoids materializing the full trace up front), compact strings
(Latin-1-backed `byte[]` instead of `char[]` when every character fits, halving memory for
ASCII-heavy strings), indified string concatenation (`+` compiles to `invokedynamic
makeConcatWithConstants` instead of a `StringBuilder` chain, allowing the JIT to pick the
concatenation strategy per call site), G1 becoming the default collector, and `Object.finalize`
being deprecated (removal only completes at Java 18, §3.16.11) round out the release.

### Java 10 — §3.16.3

`var` — local-variable type inference (not a language weakening; the identifier is still a
static, fixed type resolved at compile time, only the source-level spelling is inferred). Its
style discipline is a primary concept in the migration file (02); the OpenJDK LVTI style guide
principles and guidelines carried forward here for reference are P1–P4 (reading over writing,
local reasoning, IDE-independence, the type-explicitness tradeoff) and G1–G7 (informative names,
minimal scope, sufficient initializer information, breaking up nested expressions, not
over-programming to the interface, care with diamond/generic methods, care with literals).
`List.copyOf` / `Set.copyOf` / `Map.copyOf` return the Java 9 immutable shape but from an existing
collection, short-circuiting to the same instance if the source is already one of the `.of(...)`
immutable collections — an easy-to-miss identity optimization. `Collectors.toUnmodifiable*`
mirrors `toList`/`toSet`/`toMap` with an immutable result. `Optional.orElseThrow()` (no-arg) throws
`NoSuchElementException`, giving `Optional` parity with `Iterator.next()`'s failure mode.
Application class-data sharing (AppCDS) extends CDS (Java 5) to application classes, not just JDK
classes, cutting startup by pre-parsing class metadata into a shareable archive. Parallel full GC
for G1 replaced G1's single-threaded fallback full collection with a parallel one — a full GC
under G1 before 10 could stall for seconds on a large heap with only one thread working.

### Java 11 (LTS) — §3.16.4

`HttpClient` (`java.net.http`, incubated in 9, standardized here) is HTTP/2-aware, supports both
synchronous `send` and asynchronous `sendAsync` returning `CompletableFuture<HttpResponse<T>>` —
its request-building and connection-pooling internals are guide 10's territory. `String.isBlank`
/ `lines` / `strip` / `repeat` round out `String`'s convenience surface (`strip` is Unicode-aware
whitespace trimming, unlike the codepoint-blind `trim`). `Files.readString` / `writeString` remove
the classic `Files.readAllBytes` + `new String(bytes, UTF_8)` two-step. `Predicate.not` inverts a
method reference cleanly (`list.stream().filter(Predicate.not(String::isBlank))` versus the
uglier `s -> !s.isBlank()`). `var` in lambda parameters exists solely so a lambda parameter can
carry an annotation (`(@NonNull var clientId) -> ...`) without also writing the full type. Single-
file source launch (`java Foo.java` compiles-then-runs in one step, no `.class` on disk) is the
seed that Java 22 generalizes to multi-file (§3.16.15). ZGC and Epsilon shipped experimental —
ZGC's production-ready release is Java 15 (§3.16.8), Epsilon (a deliberately do-nothing collector
for allocation-profiling and latency-floor testing) never left experimental status because it
never needed to. Java EE and CORBA modules were removed outright (not deprecated-then-removed —
the module simply stopped being on the boot module path), Nashorn was deprecated (removed at 15),
and Flight Recorder was open-sourced from its Oracle-JDK-only commercial origin.

### Java 12 — §3.16.5

`Collectors.teeing` runs two downstream collectors over the same stream and merges their results
with a `BiFunction` — the one collector that computes two independent aggregates (e.g. average
stake size and stake count) in a single pass instead of two. `String.indent` / `transform` are
convenience string reshaping. `Files.mismatch` finds the first differing byte between two files
without loading either fully into memory. Shenandoah (low-pause-time GC, concurrent compaction)
shipped experimental alongside ZGC. Switch expressions entered preview 1 here — `case L ->` arrow
form, `yield`, exhaustiveness checking on `sealed`/enum switches — finalizing at 14 (§3.16.7).
`CompactNumberFormat` renders `1200` as `"1.2K"`.

### Java 13 — §3.16.6

Text blocks entered preview 1 (`"""`, finalizing at 15, §3.16.8); switch expressions ran preview
2, still under `--enable-preview` — the incidental-syntax churn between 12 and 14 (`break value;`
in 12's preview replaced by `yield` in 13's) is exactly the kind of design flux previewing exists
to absorb (see the primary concept above). Dynamic CDS archives let an application capture its own
class-loading footprint into a CDS archive at JVM exit (`-XX:ArchiveClassesAtExit`) instead of
requiring a separate, manually-triggered dump step. ZGC gained memory uncommit — returning unused
heap pages to the OS, which the original Java 11 ZGC did not do at all.

### Java 14 — §3.16.7

Switch expressions went **final**. Records entered preview 1 and pattern `instanceof` entered
preview 1 (`if (verdict instanceof DocumentVerdict dv)` binds `dv` only in the branch where the
type check succeeds — both finalize at 16, §3.16.9). Helpful NPE messages
(`-XX:+ShowCodeDetailsInExceptionMessages`, on by default from 15) name the exact null
sub-expression in a chained dereference (`quiz.settle(round).ledger().post()` now reports which of
`settle(round)`, `.ledger()` or the receiver was null, rather than a bare `NullPointerException`
with a line number). JFR event streaming exposed Flight Recorder data as a live stream
(`RecordingStream`) instead of only a post-hoc `.jfr` file. `jpackage` (native installer bundling)
shipped as an incubator module, finalizing at 16. CMS (Concurrent Mark Sweep) was removed — its
replacement story is G1 (default since 9) or Shenandoah/ZGC for lower pause targets.

### Java 15 — §3.16.8 `[RESEARCH]`

Text blocks went **final**. Sealed classes/interfaces entered preview 1 (finalizing at 17,
§3.16.10); records ran preview 2 with the shape essentially settled. Hidden classes (JEP 371) —
classes that cannot be discovered by name via normal classloading or reflection, used by
frameworks generating classes at runtime (Spring proxies, lambda metafactory targets,
`invokedynamic` bootstraps) — replaced the previous unsupported `sun.misc.Unsafe.defineAnonymous
Class` mechanism with a supported one; guide 06 covers hidden-class loading and unloading.
Re-verified against the JDK 21 javadoc for `MethodHandles.Lookup.defineHiddenClass`: hidden
classes are always weakly referenced by their defining loader unless created with the `STRONG`
option, so they are eligible for unloading independent of their defining class loader's lifetime —
this is the mechanism JVM-startup proxy generation relies on to avoid metaspace growth under
constant proxy churn. ZGC and Shenandoah both went production-ready. EdDSA (`Ed25519`/`Ed448`
signatures) landed in `java.security`. Nashorn was removed (its deprecation was at 11). Helpful
NPE messages went on by default (no flag needed, reversing 14's opt-in).

### Java 16 — §3.16.9 `[RESEARCH]`

Records went **final**, `instanceof` pattern matching went **final**. `Stream.toList()` is a
terser, unmodifiable-result alternative to `.collect(Collectors.toList())` — re-verified against
the JDK 21 `Stream` javadoc: `toList()`'s result type is explicitly documented as unmodifiable and
makes no guarantee of a specific implementation, whereas `Collectors.toList()`'s result is
documented as making no guarantees on mutability, serializability or thread-safety either, so the
two differ in that `toList()` is guaranteed immutable while `Collectors.toList()` is not
guaranteed anything — treat `toList()` as the safer default and `Collectors.toList()` only when a
caller genuinely needs to mutate the result. `Stream.mapMulti` lets one input element expand into
zero or more output elements via a `BiConsumer<T, Consumer<R>>` callback, avoiding the
per-element wrapper-object allocation that `flatMap` over a tiny inner stream would otherwise
incur — the mechanism guide 03 covers when comparing `flatMap` and `mapMulti` cost. Static members
became legal in inner (non-static nested) classes, removing an arbitrary Java 8-era restriction.
Strong encapsulation of JDK internals became the default (`--illegal-access` no longer defaults to
`permit`) — reflective access to non-exported JDK internals now fails by default instead of
warning. Unix-domain socket support landed in `java.net` and NIO channel APIs. `jpackage` went
final. The Vector API and the Foreign Function & Memory API (then still two APIs, Foreign-Memory
Access plus a separate Foreign Linker) began incubating — FFM's own finalization path runs to 22
(§3.16.15).

### Java 17 (LTS) — §3.16.10 `[RESEARCH]`

Sealed classes/interfaces went **final** — `permits` a closed, compiler-enumerable set of direct
subtypes, which is precisely the mechanism that makes an enum-style exhaustiveness check possible
on a class hierarchy, not just on `enum`. Pattern matching for `switch` entered preview 1 here
(finalizing at 21, §3.16.14 — see the dedicated primary concept below). `RandomGenerator` (JEP
356) is a redesigned `java.util.random` hierarchy (`RandomGeneratorFactory`,
algorithm-selectable generators like `Xoshiro256PlusPlus`) that supersedes `java.util.Random`'s
single linear-congruential algorithm without deprecating it. Always-strict floating point (JEP
306) removed the `strictfp` distinction — every `float`/`double` operation is now
IEEE 754-strict everywhere, closing a rarely-hit but real platform-dependent rounding
inconsistency from the pre-Java-17 non-strict default on x87-era hardware (long since moot on
modern CPUs, which is exactly why the JEP could finally simplify the spec). Context-specific
deserialization filters (`ObjectInputFilter` configurable per call site, not just JVM-wide)
harden `ObjectInputStream` against the deserialization-gadget-chain class of vulnerability — guide
13's territory for the security framing. The Security Manager was deprecated for removal (removal
completes at 24, §3.16.17); the applet API was deprecated (browsers had already dropped applet
support years earlier — this was cleanup, not a live removal of a used feature). The macOS/AArch64
(Apple Silicon) port shipped.

### Java 18 — §3.16.11 `[RESEARCH]`

UTF-8 became the default charset for `Charset.defaultCharset()`, `new String(byte[])`, file I/O
without an explicit charset, and more — before 18, the default was platform-dependent (`Cp1252` on
Windows, differing locale defaults elsewhere), meaning a `Files.readString(path)` with no explicit
charset could silently mojibake a UTF-8 file on Windows and read fine on Linux. Anyone claiming a
bare `new String(bytes)` is "portable" is a version trap that 18 fixes going forward but does not
retroactively fix on JVMs younger than 18. The simple web server (`jwebserver` CLI, `com.sun.net
.httpserver`) is a minimal static file server for local testing, not a production HTTP server.
`@snippet` in javadoc lets code examples be validated by the compiler rather than living as
unchecked comment text. The internet address resolution SPI (JEP 418) let `InetAddress` resolution
be pluggable instead of hardwired to the OS resolver. Finalization (`Object.finalize`) was
deprecated for removal (JEP 421) — the removal target has since moved (still not removed as of 25,
§3.16.19, though disabled by default in some later builds; treat "when it will be fully removed"
as unresolved rather than asserting a release). Pattern switch ran preview round 2.

### Java 19 — §3.16.12

Virtual threads entered preview 1 (JEP 425) — treated in full as a primary concept below, since
this is the release history's highest-leverage interview topic. Structured concurrency entered
**incubator** status (not preview — `StructuredTaskScope` lived in
`jdk.incubator.concurrent` here, a JDK-internal-module incubation stage that precedes even a
language/API preview, meaning no `--enable-preview` flag existed yet; you opted in by
`--add-modules jdk.incubator.concurrent`). Record patterns entered preview 1 (destructuring a
record in a pattern position: `case StakeSplit(var bonus, var cash) -> ...`, finalizing at 21).
Pattern switch ran preview round 3. FFM (now unified as one Foreign Function & Memory API) entered
preview 1. The Linux/RISC-V port shipped.

### Java 20 — §3.16.13

No language feature went final in this release — all four of virtual threads, structured
concurrency, record patterns and pattern switch were re-previewed (their second, second, second
and fourth preview rounds respectively), and scoped values entered **incubator**. A release with
zero finalized language features is itself worth remembering for the "what shipped in 20"
interview trap: the honest answer is "nothing finalized — it was the widest re-preview release in
the whole Amber/Loom run," not silence, and not guessing a feature from a neighboring release.

### Java 21 (LTS) — §3.16.14 `[RESEARCH]`

Virtual threads went **final** (JEP 444) — full treatment below. Record patterns went **final**
(JEP 440), including nested destructuring (`case Movement(StakeSplit(var bonus, var cash), var
timestamp) -> ...`). Pattern matching for `switch` went **final** (JEP 441) — full treatment
below, including the exhaustiveness exception-type correction. Sequenced collections (JEP 431)
retrofit `SequencedCollection`, `SequencedSet` and `SequencedMap` interfaces onto the collections
hierarchy, giving every ordered collection `getFirst()` / `getLast()` / `addFirst()` /
`addLast()` / `reversed()` uniformly — before 21, "give me a reversed view of this `LinkedHashMap`"
had no library answer; guide 02 covers the interface retrofit's default-method mechanics.
Generational ZGC (opt-in via `-XX:+ZGenerational` on 21, default from 23 per §3.16.16) added a
young/old generation split to ZGC's previously single-generation design, cutting the CPU cost of
young-object collection. The key encapsulation API (`javax.crypto.KEM`, JEP 452) standardizes
key-encapsulation-mechanism cryptography (relevant to post-quantum key exchange). Preview in this
release: string templates (JEP 430, later withdrawn — §3.16.16), structured concurrency (JEP 453,
preview — the package moved out of incubation into `java.util.concurrent`, still needing
`--enable-preview`), scoped values (JEP 446, preview), unnamed patterns and variables (JEP 443,
`case StakeSplit(var bonus, _) -> ...` where `_` discards a binding you don't need), and unnamed
classes with instance `main` (JEP 445, the on-ramp for beginners — `void main() { ... }` with no
enclosing class or `public static`).

### Java 22 — §3.16.15 `[RESEARCH]`

Unnamed variables and patterns went **final**. FFM went **final** (JEP 454) — `Arena`,
`MemorySegment`, `Linker`, replacing JNI for calling native code without writing C glue; the
memory-safety and layout mechanics are guide 06's territory. Multi-file source launch generalized
Java 11's single-file launcher to a small program spread across multiple `.java` files run
directly with `java`. Statements before `super()` entered preview (JEP 447 — validation logic
allowed to run before the mandatory superclass constructor call, as long as it does not touch
`this`). Stream gatherers entered preview 1 (finalizing at 24, §3.16.17). String templates ran
preview round 2 (the last round before withdrawal). Region pinning for G1 reduced G1's evacuation
failure rate under high humongous-object churn.

### Java 23 — §3.16.16 `[RESEARCH]`

**String templates were withdrawn** (JEP process explicitly retracted the feature rather than
finalizing or re-previewing it) — the JEP 430 preview shape (`STR."Stake \{stakeId} reserved"`) is
gone from 23 onward with no replacement shipped in 23, 24 or 25; a "redesigned string-template
proposal" is listed as still in flight (§3.16.19). This is the sharpest "what's new" trap in the
whole timeline: candidates who read a 2023 blog post about string templates and repeat it as
current Java 21+ fact are stating a withdrawn feature as live. Stream gatherers ran preview round
2. Primitive types in patterns entered preview 1 (`case Integer i when i > 0 ->` extended to
primitive type patterns directly, not just boxed). Markdown javadoc (JEP 467) let `///`-style
Markdown replace HTML-in-comments javadoc syntax. Generational ZGC became the **default** ZGC
mode. `sun.misc.Unsafe`'s memory-access methods were deprecated for removal (JEP 471) — the
FFM API (final since 22) is the sanctioned replacement.

### Java 24 — §3.16.17 `[RESEARCH]`

Stream gatherers went **final** (JEP 485) — `Stream.gather(Gatherer)` generalizes intermediate
stream operations beyond the fixed `filter`/`map`/`flatMap`/`sorted` set to arbitrary stateful,
possibly-short-circuiting transformations (a windowing gatherer, a fold-with-early-exit) that no
built-in operation could express. JEP 491 is the pinning-removal correction carried forward from
the previous guide in full: **`synchronized` no longer pins a virtual thread from Java 24
onward**, because `Object` monitors became continuation-aware — the JVM can now unmount the
carrier thread even while a virtual thread holds a monitor, which removes the single most common
cause of the `jdk.VirtualThreadPinned` JFR event on 21–23. Native and foreign-frame pinning (JNI
calls, FFM calls) is untouched by JEP 491 and still pins on 24 — the event survives, just with a
narrower cause set. The Class-File API went **final** (JEP 484) — a standard, versioned API for
parsing and generating `.class` files, replacing the ecosystem's reliance on ASM/BCEL-style
third-party bytecode libraries for tooling that must track new class-file features release over
release. Scoped values and structured concurrency were both re-previewed again (their fourth and
fourth rounds respectively). AOT class loading and linking previewed a training-run-based startup
optimization. Compact object headers shipped experimental (shrinking the 12–16 byte object header
toward 8 bytes on 64-bit — guide 06's memory-layout territory). The Security Manager was
**permanently disabled** (JEP 486) — not merely deprecated any further; `-Djava.security.manager`
now throws at startup rather than installing a manager.

### Java 25 (LTS) — §3.16.18

Scoped values went **final** (JEP 506) — an immutable, dynamically-scoped alternative to
`ThreadLocal` designed around virtual threads (a scoped value's lifetime is bound to a lexical
`ScopedValue.where(...).run(...)` block, not to a thread's full lifetime, avoiding the
`ThreadLocal` leak pattern where a pooled platform thread carries stale state into its next task).
Compact source files and instance `main` went **final** (JEP 512, the Java 21 preview generalized
and finalized). Module import declarations went **final** (JEP 511 — `import module
java.base;` imports every exported package of a module in one line, aimed at the compact-source-
file / beginner on-ramp rather than large codebases). Flexible constructor bodies went **final**
(JEP 513 — the Java 22 preview on statements before `super()`, renamed and finalized).
Structured concurrency ran its **fifth** preview round (JEP 505) — the API shape changed from
Java 21's public constructors (`new ShutdownOnFailure()`) to static factory methods
(`StructuredTaskScope.open(...)`) and the fixed `ShutdownOnFailure`/`ShutdownOnSuccess` pair was
replaced by a composable `Joiner` — see the corrections block referenced in the virtual-threads
primary concept below for both API shapes side by side. Primitive types in patterns ran preview
round 3. Stable values entered preview (a `StableValue<T>` holder computed at most once,
positioned as a more precise alternative to double-checked-locking lazy-init idioms — guide 05's
territory for the concurrency framing). PEM encodings (`java.security.PEMEncoder`/`PEMDecoder`)
standardized reading/writing PEM-format keys and certificates without a third-party library.
Generational Shenandoah brought Shenandoah's pause-time story the same young/old split ZGC got at
21.

### Still in flight — §3.16.19

As of this file's target date, the following have not finalized on any shipped release: structured
concurrency (sixth preview via JEP 525, with a seventh, JEP 533, proposed for the next release —
**Unverified:** which exact release JEP 533 targets, since it was still a draft at time of
writing), primitive type patterns (third preview on 25, no finalization JEP filed yet), stable
values (first preview on 25), Valhalla value classes (no preview JEP has shipped in a released
JDK as of 25 — Valhalla remains a separate early-access build, not a mainline preview), derived
record creation (a proposed `with`-expression style copy mechanism for records, still at the
JEP-candidate stage), and a redesigned string-template proposal replacing the JEP 430 design
withdrawn at 23. Treat every one of these as **not usable today** regardless of what a given
blog post from 2024 or 2025 claims — the correct interview answer is "previewing, not final, as
of the last LTS I've used," named explicitly rather than asserted as shipped.

---

## Primary concept: pattern matching for switch — the exhaustiveness trap that changed underneath you

**Mental model.** An exhaustive `switch` expression over a sealed hierarchy is not "a switch the
compiler happens to accept" — the compiler inserts a **synthetic default arm** into the bytecode
regardless of how exhaustive your source looks, because a class file compiled today can be loaded
alongside a sibling class file recompiled tomorrow with one more permitted subtype added to the
sealed hierarchy. That synthetic arm is a safety net for exactly that skew, and it throws.

**Why it exists.** Separate compilation means `Verdict`'s sealed permits-list and
`StakeSettlementResolver`'s switch over `Verdict` do not have to be recompiled together. If someone
adds a fifth subtype to the `Verdict` sealed hierarchy (alongside `DocumentVerdict`,
`ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict`) and redeploys only that module, every switch
compiled against the old four-case hierarchy is now non-exhaustive at runtime even though it
compiled cleanly against the old shape. The JVM needs a defined failure mode for that moment,
not undefined behavior or a silent fall-through.

**When to reach for it, and when not.** Prefer an exhaustive `switch` expression over any sealed
hierarchy or enum when every branch must produce a value — it is the only construct that gives you
a compile-time exhaustiveness guarantee at all. Reach for a plain `if`/`else if` chain instead when
the type being tested is not sealed (an open class hierarchy has no permits-list for the compiler
to check against, so there is no exhaustiveness guarantee to gain).

**How it works — the version delta itself.** The synthetic default arm exists at every release
that has pattern matching for switch, but **the exception type it throws changed at Java 21**, and
the syllabus material claiming otherwise has it backwards. Verified on this machine by compiling
the sealed hierarchy and the switch in separate compilation units, adding a case, and recompiling
only the hierarchy:

```
release 14 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 17 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 21 -> Exception in thread "main" java.lang.MatchException
```

and in `javap -c` on the `--release 21` class file, the synthetic default arm compiles to:

```
36: new           #19    // class java/lang/MatchException
42: invokespecial #21    // Method java/lang/MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
45: athrow
```

Read it instruction by instruction: `new #19` allocates an uninitialized `MatchException`
instance; `invokespecial #21` calls its `(String, Throwable)` constructor, meaning the JVM can
attach both a descriptive message and a cause (typically `null` for the plain exhaustiveness case,
non-null for the `ClassCastException`-wrapping case described below); `athrow` throws it.

**[VERSION-TRAP]** The correct statement, stated at both ends and naming the release that changed
it: the synthetic default throws `IncompatibleClassChangeError` on Java 14 through 20, and
`java.lang.MatchException` from Java 21 onward, constructed with the `(String, Throwable)`
two-argument constructor. Any source — including this syllabus's own leaf text before this
correction — that states `MatchException` "replaced" `IncompatibleClassChangeError` as if the
older type came first and the newer type is strictly later has the chronology right but glosses
the release boundary that actually matters for an interview: name **21** as the pivot, not "recent
Java."

**Example — an exhaustive switch over QuizStakes' verdict hierarchy:**

```java
sealed interface Verdict permits DocumentVerdict, ScreeningVerdict, ReviewVerdict, WealthVerdict {}
record DocumentVerdict(String outcome, String reason) implements Verdict {}
record ScreeningVerdict(String outcome, String reason) implements Verdict {}
record ReviewVerdict(String outcome, String reason) implements Verdict {}
record WealthVerdict(String outcome, String reason) implements Verdict {}

final class VerdictRouter {
    String routeToNextGate(Verdict verdict) {
        return switch (verdict) {
            case DocumentVerdict dv when dv.outcome().equals("REJECTED") -> "AA-690";
            case DocumentVerdict dv -> "AA-611";
            case ScreeningVerdict sv -> "AA-501";
            case ReviewVerdict rv -> "AA-711";
            case WealthVerdict wv -> "AO-141";
        };
    }
}
```

No `default` arm is written, and none is needed for the compiler to accept this — the four
`permits` types are covered. The synthetic `MatchException`-throwing arm is inserted by the
compiler regardless, invisible in source, present in bytecode.

**Pitfall:** believing an exhaustive sealed-hierarchy switch can never throw at runtime, because
"the compiler already proved it's exhaustive." The compiler proved it exhaustive **against the
class files present at compile time.** A classpath skew — an old `VerdictRouter.class` next to a
`Verdict.class` recompiled with a fifth permitted subtype — reintroduces exactly the failure the
compiler thought it had eliminated, just moved to runtime and renamed `MatchException`.

**Interview:** "does an exhaustive switch over a sealed type need a default case?" — no, and the
compiler will reject an unreachable one if you add it as a plain `default` after truly exhaustive
cases; but the JVM still inserts a synthetic default that throws `MatchException` (21+) or
`IncompatibleClassChangeError` (14–20) to guard against separately-compiled classpath skew.

> **Definition:** exhaustive pattern matching for `switch` is a compile-time guarantee checked
> against the sealed hierarchy's permits-list at compile time, backstopped at runtime by a
> compiler-synthesized default arm that throws `MatchException` from Java 21 onward
> (`IncompatibleClassChangeError` on 14–20) if the classes actually loaded disagree with what was
> compiled against.

---

## Primary concept: virtual threads — preview to final, and the scheduler defaults nobody states precisely

**Mental model.** A virtual thread is a `Thread` object multiplexed onto a small pool of carrier
platform threads by a `ForkJoinPool` scheduler, unmounting the carrier whenever the virtual thread
blocks on a supported operation and remounting it (possibly onto a different carrier) when the
blocking operation completes. `Thread.ofVirtual()` and `Executors.newVirtualThreadPerTaskExecutor
()` are the entry points; **[X-REF 05]** the continuation/unmount mechanism itself, and what makes
an operation "supported" for unmounting versus pinning, is guide 05's full territory — the load-
bearing fact for this file is the release timeline and the scheduler's actual tuning defaults.

**Why it exists.** A platform thread costs roughly a megabyte of stack plus an OS thread-table
entry, so a thread-per-request server tops out in the low thousands of concurrent requests before
context-switch and memory overhead dominate. QuizStakes' 55k peak concurrent sessions and 1,200
stake reservations/sec cannot be served one platform thread per in-flight request without either
an async/reactive rewrite (steep API cost) or a bounded-thread-pool-plus-queue model (adds queueing
latency under burst). Virtual threads let the thread-per-request programming model — the simplest
one to reason about and debug — scale to that concurrency without either compromise.

**When to reach for it, and when not.** Reach for virtual threads for I/O-bound, high-fan-out work
— exactly QuizStakes' pattern of one virtual thread per inbound settlement request, blocking on
the PSP call (p50 240ms) and the Quiz Engine call without tying up a scarce platform thread. Do
not reach for them for CPU-bound work — a virtual thread blocked on CPU-bound computation (no I/O,
no supported blocking point) pins its carrier exactly like a platform thread would, gaining
nothing over `ForkJoinPool.commonPool()`'s work-stealing model, which is the right tool for a
CPU-bound parallel-stream decomposition instead.

**How it works — the timeline.** Virtual threads entered preview at 19 (JEP 425), re-previewed
unchanged in shape at 20 (JEP 436), and went **final** at 21 (JEP 444) — one of only two rounds of
preview before finalization, the shortest path in this file's whole timeline, which is itself a
signal of how settled the design already was going in.

**How it works — the scheduler's defaults, verified against `VirtualThread
.createDefaultScheduler()` at the jdk-21+35 tag, not recalled:**

```java
int parallelism, maxPoolSize, minRunnable;
String parallelismValue = System.getProperty("jdk.virtualThreadScheduler.parallelism");
String maxPoolSizeValue = System.getProperty("jdk.virtualThreadScheduler.maxPoolSize");
String minRunnableValue = System.getProperty("jdk.virtualThreadScheduler.minRunnable");
if (parallelismValue != null) {
    parallelism = Integer.parseInt(parallelismValue);
} else {
    parallelism = Runtime.getRuntime().availableProcessors();
}
if (maxPoolSizeValue != null) {
    maxPoolSize = Integer.parseInt(maxPoolSizeValue);
    parallelism = Integer.min(parallelism, maxPoolSize);
} else {
    maxPoolSize = Integer.max(parallelism, 256);
}
if (minRunnableValue != null) {
    minRunnable = Integer.parseInt(minRunnableValue);
} else {
    minRunnable = Integer.max(parallelism / 2, 1);
}
boolean asyncMode = true; // FIFO
return new ForkJoinPool(parallelism, factory, handler, asyncMode,
             0, maxPoolSize, minRunnable, pool -> true, 30, SECONDS);
```

Reading it line by line, on this file's standard 8-core box (§ "one machine, one set of core
numbers" below): `parallelism` defaults to `availableProcessors()` = **8**.
**`maxPoolSize` defaults to `Integer.max(parallelism, 256)` = 256 — a floor, not a flat constant.**
On a machine with more than 256 available processors, `maxPoolSize` equals `parallelism` instead;
"the default is 256" is only true below 257 cores, and an interview answer that states it as a
flat number without the `max(...)` is stating the syllabus-stale version. Setting
`jdk.virtualThreadScheduler.maxPoolSize` below the processor count also clamps `parallelism` down
to match it — one system property silently moves two numbers, not one. `minRunnable` defaults to
`Integer.max(parallelism / 2, 1)` = **4** on 8 cores — a third tuning property
(`jdk.virtualThreadScheduler.minRunnable`) that most material never names at all. The scheduler
is, mechanically, a `ForkJoinPool` built with `asyncMode = true`; the source's own inline comment
on that line — `// FIFO` — is the evidence for the FIFO-scheduling claim, not an inference, and is
worth quoting rather than asserting. The pool keeps idle workers alive for 30 seconds
(`30, SECONDS`) and accepts unbounded submissions (`pool -> true` as the saturation predicate,
meaning the pool never rejects work — backpressure has to come from somewhere else in the
application, not the scheduler).

**Example — sizing the settlement fan-out against the scheduler defaults:**

```java
// One virtual thread per stake settlement; the ForkJoinPool scheduler
// (parallelism 8, maxPoolSize 256, minRunnable 4 on this file's reference box)
// carries all of them, unmounting each on the PSP call's blocking I/O.
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<Movement>> settlements = new ArrayList<>();
    for (RoundId roundId : openRounds) {
        settlements.add(executor.submit(() -> settleStake(roundId)));
    }
    for (Future<Movement> settlement : settlements) {
        Movement movement = settlement.get();
    }
}
```

At QuizStakes' 1,200 reservations/sec peak with a PSP p50 of 240ms, Little's law says the
in-flight population averages `1200 * 0.24` = **288** concurrent settlements — comfortably inside
the scheduler's 256-and-up `maxPoolSize` headroom on carriers, because virtual threads blocked on
I/O do not occupy a carrier at all; the 288 figure bounds the number of *virtual* thread objects
in flight, not the number of platform carrier threads, which stays near `parallelism` = 8.

**Pitfall:** `synchronized` pins a virtual thread to its carrier on Java 21 — a virtual thread
inside a `synchronized` block cannot be unmounted even while blocked on I/O, defeating the whole
scaling argument for exactly that critical section. `jdk.VirtualThreadPinned` is the JFR event
that surfaces it. **[VERSION-TRAP]** JEP 491 makes `Object` monitors continuation-aware from
**Java 24** onward, removing `synchronized` as a pinning cause; "use `ReentrantLock` instead of
`synchronized` around virtual-thread code" is therefore a correct answer **on 21 through 23** and
an unnecessary migration from 24 onward — state which release you mean rather than giving the
rule as timeless. Native and foreign-frame calls (JNI, FFM) still pin at every release including
24, so `jdk.VirtualThreadPinned` never fully disappears from the diagnostic vocabulary.

**Insight:** structured concurrency's two shipped API shapes are not a deprecation story, they are
a version-delta story in their own right, and belong here rather than left as "still evolving."
Java 21 (JEP 453, preview): public constructors (`new ShutdownOnFailure()`), `fork` returning
`Subtask<T>` (not `Future<T>`), fixed policies `ShutdownOnFailure`/`ShutdownOnSuccess`, package
`java.util.concurrent` (moved out of `jdk.incubator.concurrent` at this release). Java 25 (JEP
505): public constructors replaced by static `open()` factories, and the two fixed shutdown
policies replaced by a single composable `Joiner` type. A candidate asked "what does structured
concurrency look like" without being told which release should ask which release is meant before
answering, because the two API shapes are not source-compatible with each other.

**Interview:** "how many virtual threads can I run at once, and what limits it?" — there is no
hard cap on virtual thread *object* count (they are ordinary heap objects with a small stack
footprint until they actually run), but the number that can be simultaneously **runnable and not
yet scheduled onto a carrier** is bounded by the scheduler's `ForkJoinPool` parallelism (8 by
default on this file's reference box) plus its ability to grow `maxPoolSize` (up to `max(8, 256)`
= 256) when tasks blocked on I/O free up scheduling headroom — the honest one-line answer names
both numbers and the `max(...)` relationship between them, not a flat "unlimited" or a flat "256."

> **Definition:** a virtual thread is a JDK-scheduled, continuation-backed `Thread` multiplexed
> by default onto a `ForkJoinPool` carrier pool sized to `availableProcessors()` (floor 1, ceiling
> `max(parallelism, 256)` for `maxPoolSize`), finalized at Java 21 after two preview rounds,
> unmounting its carrier on every supported blocking operation except a held monitor before
> Java 24 or a native/foreign call at any release.

---

## Primary concept: how to answer "what's new in Java N" — §3.16.22

**Mental model.** The question is never really "list every JEP in release N." It is "can you
navigate a release you may not have used in production, extract the two or three items that
matter, and reason about their tradeoffs on the spot." Treat it as a **structured retrieval task
with a fixed output shape**, not an open recall task.

**Why it exists.** Interviewers ask it because a flat, unstructured answer ("well there's a bunch
of stuff, pattern matching, uh, some GC things") signals a candidate who has only skimmed release
notes, while a structured answer signals someone who actually reasons about platform upgrades as
part of their job — which for a Staff-track candidate is a real recurring task (deciding whether
to move QuizStakes' payment services from 17 to 21, for instance).

**When to reach for it, and when not.** Use the three-feature shape for any "what's new in Java
N" or "why would you upgrade from X to Y" question. Do not use it as a substitute for depth
questions — if the interviewer follows up "how does the scheduler actually work," that is the
virtual-threads primary concept above, not this one; this shape is for breadth, not the follow-up.

**How it works.** The fixed shape is: **name three features, one problem each solves, one trap
each, and the release you personally run in production** — in that order, every time, regardless
of which release is asked about.

**The diagram — D-166, the consolidated feature → version table, at the point every "when did X
finalize" question needs it:**

| Feature | First preview | Final | JEP(s) | Preview on 21? | One-line summary |
|---|---|---|---|---|---|
| Lambdas / streams / `Optional` | — (Java 8, no preview era) | 8 | JSR 335 / 335 | No | Functional interfaces + `invokedynamic`-backed lambdas; lazy stream pipelines |
| `var` (LVTI) | — | 10 | JEP 286 | No | Local-variable type inference, spelling only |
| Switch expressions | 12 (JEP 325) | 14 | 325 / 354 / 361 | No | `->` arrow form, `yield`, exhaustiveness on sealed/enum |
| Text blocks | 13 (JEP 355) | 15 | 355 / 368 / 378 | No | `"""`-delimited multi-line strings, incidental-whitespace stripping |
| Records | 14 (JEP 359) | 16 | 359 / 384 / 395 | No | Nominal, transparent, `equals`/`hashCode`/`toString` carriers |
| `instanceof` pattern | 14 (JEP 305) | 16 | 305 / 375 / 394 | No | Type-test + bind in one expression |
| Sealed classes | 15 (JEP 360) | 17 | 360 / 397 / 409 | No | Closed, compiler-enumerable subtype set |
| Pattern matching for `switch` | 17 (JEP 406) | 21 | 406 / 420 / 427 / 433 / 441 | No | Type patterns, guards, record deconstruction in `switch` |
| Record patterns | 19 (JEP 405) | 21 | 405 / 432 / 440 | No | Destructure a record in a pattern position |
| Virtual threads | 19 (JEP 425) | 21 | 425 / 436 / 444 | No | Lightweight, continuation-backed `Thread` |
| Sequenced collections | — (no preview) | 21 | 431 | No | `getFirst`/`getLast`/`reversed()` retrofit |
| Structured concurrency | 19 (incubator) | not final on 21 | 428 / 437 / 453 / 480 / 499 / 505 | Yes (preview) | Fork/join task lifetimes scoped to one block |
| Scoped values | 20 (incubator) | 25 | 429 / 446 / 464 / 481 / 487 / 506 | Yes (preview) | Immutable, lexically-scoped thread-local alternative |
| String templates | 21 (JEP 430) | **withdrawn at 23** | 430 / 459 | Yes (preview, later withdrawn) | Interpolated string literals (`STR."..."`) — no longer available |
| Unnamed patterns/variables | 21 (JEP 443) | 22 | 443 / 456 | Yes (preview) | `_` discards an unused binding |
| Unnamed classes / instance `main` | 21 (JEP 445) | 25 | 445 / 463 / 477 / 495 / 512 | Yes (preview) | Beginner on-ramp: no class/`public static` boilerplate |
| FFM API | 19 (preview, then split/merged) | 22 | 424 / 434 / 442 / 454 | No | Call native code and manage off-heap memory without JNI |
| Stream gatherers | 22 (JEP 461) | 24 | 461 / 473 / 485 | No | User-defined, possibly-stateful intermediate stream ops |

**D-166** — The consolidated feature → version table.

**A minimal concrete example — a fully worked "what's new in Java 21" answer** for QuizStakes'
own upgrade decision (17 to 21 on the payment services, §12's flows):

```
Feature 1: virtual threads (final, JEP 444).
  Problem it solves: the payment services block on the PSP (p50 240ms authorize)
  and the Quiz Engine per settlement; platform-thread-per-request tops out around
  a few thousand concurrent requests before stack memory and context-switch
  overhead dominate. Virtual threads let thread-per-request scale to the 55k peak
  concurrent sessions QuizStakes needs.
  Trap: synchronized still pins on 21 (fixed only at 24, JEP 491) — any legacy
  synchronized block in the settlement path needs auditing before the upgrade,
  not after.
  Production release I run: 21.

Feature 2: record patterns + pattern matching for switch (both final, JEP 440/441).
  Problem it solves: routing a Verdict (DocumentVerdict/ScreeningVerdict/
  ReviewVerdict/WealthVerdict) used to need a chain of instanceof-and-cast; now
  it is one exhaustive switch with compiler-checked coverage.
  Trap: the compiler's exhaustiveness check is only as good as what was compiled
  against — a classpath skew still throws at runtime (MatchException on 21+,
  see the dedicated section above), so exhaustive-switch is a compile-time aid,
  not a runtime guarantee against a bad deploy.
  Production release I run: 21.

Feature 3: sequenced collections (final, JEP 431).
  Problem it solves: reversed-order iteration over the ledger's recent-entries
  view used a manual ListIterator walk; SequencedCollection.reversed() replaces
  it with a one-line, allocation-free reversed view.
  Trap: reversed() returns a view, not a copy — mutating the reversed view
  mutates the original SequencedCollection, which surprises anyone assuming
  "reversed" implies "independent copy."
  Production release I run: 21.
```

**The gotcha.** Naming three features from three *different* releases when asked "what's new in
21" is the single most common failure mode of this answer shape — it signals the candidate is
reciting a general Java timeline rather than actually distinguishing release boundaries. Anchor
every feature named to the release actually asked about, and if a genuinely relevant fact belongs
to a neighboring release (record patterns previewed at 19, not 21), say so explicitly rather than
letting it blur into "21 stuff."

> **Definition:** answering "what's new in Java N" well means naming exactly three features that
> finalized (or meaningfully changed) in N, one concrete problem each solves, one trap each, and
> the release you actually run — never a flat feature list, never features borrowed silently from
> a different release.

---

## The consolidated removed-or-disabled table — §3.16.21

**D-167**, at the point every "is X still available" question needs it:

| Item | Deprecated in | Removed / disabled in | Replacement | Symptom on upgrade |
|---|---|---|---|---|
| Nashorn (JS engine) | 11 | 15 (removed) | GraalVM JS, or no in-JVM JS engine | `ClassNotFoundException` for `jdk.nashorn.api.scripting.*`; `javax.script` finds no JS `ScriptEngine` |
| Java EE modules (`java.xml.ws`, `java.xml.bind`, etc.) | 9 (marked for removal) | 11 (removed) | Jakarta EE artifacts on the classpath as ordinary dependencies | `NoClassDefFoundError` for `javax.xml.bind.*` etc. at runtime |
| CORBA | 9 (marked for removal) | 11 (removed) | gRPC, REST, or a third-party CORBA implementation | `NoClassDefFoundError` for `org.omg.CORBA.*` |
| Applets | 9 (API deprecated) | 17 (API deprecated for removal); browsers had already dropped support years earlier | None — browser plugin model is gone | Compile-time deprecation warnings on `java.applet.*`; no runtime removal as of 25 |
| Security Manager | 17 | 24 (permanently disabled) | OS-level sandboxing, container isolation, capability-scoped service accounts | `-Djava.security.manager` throws `UnsupportedOperationException` at startup on 24+ |
| Finalization (`Object.finalize`) | 18 (deprecated for removal, JEP 421) | not removed as of 25 — **Unverified:** exact future removal release | `Cleaner` (`java.lang.ref.Cleaner`) or try-with-resources | Compile-time deprecation warning only, as of 25; no runtime break yet |
| 32-bit x86 port | — (platform support, not an API) | 9 (removed as a supported build target) | 64-bit x86/AArch64 builds only | Build/install failure choosing a 32-bit x86 JDK distribution post-9 |
| `sun.misc.Unsafe` memory-access methods | 23 (JEP 471) | not removed as of 25 — flagged for eventual removal | Foreign Function & Memory API (final since 22) | Compile-time deprecation warning on 23+; `Unsafe` object-field access (`objectFieldOffset`, etc.) is unaffected by JEP 471, only memory-access methods are targeted |

**D-167** — The consolidated removed-or-disabled table.

**Pitfall:** treating "deprecated" and "removed" as interchangeable when answering an upgrade-risk
question. The Security Manager's own timeline — deprecated at 17, still fully functional through
21, 22 and 23, and only permanently disabled at 24 — is the clearest counterexample: a service
still setting `-Djava.security.manager` on Java 21 is on borrowed time, not already broken, and
the correct advice differs sharply depending on which of those two states it is actually in.

---

## Pitfalls

### Stating "the virtual thread scheduler's maxPoolSize is 256" as a flat constant

**Wrong**

```java
// "On any machine, up to 256 virtual threads can be scheduled at once" — false.
System.out.println(ForkJoinPool.commonPool().getParallelism()); // irrelevant pool anyway
```

**Right**

```java
// maxPoolSize = Integer.max(availableProcessors(), 256).
// On a 512-core box, maxPoolSize is 512, not 256 — 256 is a floor.
int floor = Integer.max(Runtime.getRuntime().availableProcessors(), 256);
```

**Why people believe it:** almost every blog post, and even some conference talks, quote "256" as
the number because it is the number on every laptop and every CI runner they tested on — machines
with well under 256 cores, where the `max(...)` floor is the number that always wins.

### Claiming `summingInt` is overflow-safe like `averagingInt`

**Wrong**

```java
int total = quizStakesStakes.stream().collect(Collectors.summingInt(Stake::amountMinorUnits));
// silently wraps once the running sum exceeds Integer.MAX_VALUE
```

**Right**

```java
long total = quizStakesStakes.stream().collect(Collectors.summingLong(Stake::amountMinorUnits));
// summingLong accumulates into a long[1] slot — the actual overflow-safe collector
```

**Why people believe it:** `averagingInt` genuinely does accumulate into a `long[2]` slot (sum,
count) and is safe, so it is easy to assume its sibling `summingInt` shares the same safety —
verified against `Collectors` at the jdk-21+35 tag, `summingInt`'s accumulator is `new int[1]`
holding the sum **as an `int`**, with exactly `IntStream.sum()`'s silent-overflow behavior. Proved
on this machine (`javac --release 21`), summing `1_000_000_000` three times gives `summingInt :
-1294967296` against `summingLong: 3000000000` (the correct total).

### Answering "what's new in Java N" as an undifferentiated feature list

**Wrong**

```
"Java 21 has virtual threads, pattern matching, sealed classes, records,
text blocks, and a bunch of other stuff from the last few years."
```

**Right**

```
Three features that finalized in 21 specifically: virtual threads (JEP 444),
record patterns (JEP 440), pattern matching for switch (JEP 441) — sealed
classes finalized at 17, records at 16, text blocks at 15, not 21.
```

**Why people believe it:** once a feature has shipped, it is simply "in Java" from the user's
day-to-day perspective, and the specific release boundary stops mattering for writing code — it
only starts mattering again the moment an interviewer asks about it.

## Cheat sheet

| Item | Value |
|---|---|
| LTS releases | 8, 11, 17, 21, 25 |
| Release cadence | 6 months, since 9 |
| Preview flag | `--enable-preview` on both `javac` and `java` |
| Preview class-file marker | minor version `0xFFFF` |
| Switch expr. final | 14 |
| Text blocks final | 15 |
| Records / `instanceof` pattern final | 16 |
| Sealed classes final | 17 |
| Record patterns / pattern switch / virtual threads final | 21 |
| Structured concurrency API shape 1 (constructors) | 21 (preview) |
| Structured concurrency API shape 2 (`open()`, `Joiner`) | 25 (still preview, JEP 505) |
| String templates | preview 21–22, **withdrawn 23** |
| FFM final | 22 |
| `synchronized` stops pinning | 24 (JEP 491) |
| Security Manager permanently disabled | 24 |
| Scoped values final | 25 |
| Exhaustive switch synthetic default throws | `IncompatibleClassChangeError` (14–20) → `MatchException` (21+) |
| VT scheduler defaults (8-core box) | parallelism 8, maxPoolSize `max(8,256)`=256, minRunnable `max(4,1)`=4 |
| `summingInt` overflow | yes, `int[1]` — use `summingLong` |

## Self-test

**Q1.** Why does `VirtualThread.createDefaultScheduler()`'s `maxPoolSize` default to
`Integer.max(parallelism, 256)` rather than a flat `256`?

<details><summary>Answer</summary>

Because on a machine with more than 256 available processors, capping the pool at a flat 256
would leave scheduling headroom below the hardware's actual parallelism. The `max(...)` makes 256
a floor that only binds on machines at or below that core count — which is every laptop and most
CI runners, which is why the flat-256 folklore persists — while scaling up automatically on larger
hardware.

</details>

**Q2.** A candidate says "Java 21 added string interpolation with `STR."..."` syntax." What is
wrong with that statement as of a Java 25 target?

<details><summary>Answer</summary>

String templates (JEP 430) previewed at 21, re-previewed at 22, and were **withdrawn** at 23 —
they are not available on any release from 23 onward, and no replacement has shipped as of 25 (a
redesign is only a proposal in flight). The statement was true only for someone running 21 or 22
with `--enable-preview`; presented as current fact on a later target version it is stating a
withdrawn feature as live.

</details>

**Q3.** An exhaustive `switch` over `Verdict` (sealed, four permitted subtypes) throws at runtime
after a deploy. What exception type appears on Java 21, what type would have appeared on Java 17,
and why does the exhaustive check not prevent this?

<details><summary>Answer</summary>

`java.lang.MatchException` on Java 21+ (`IncompatibleClassChangeError` on 14–20). The compiler's
exhaustiveness check only validates against the class files present at compile time; if
`Verdict.class` is later recompiled with a fifth permitted subtype and redeployed without
recompiling `VerdictRouter.class`, the switch that was exhaustive at compile time is no longer
exhaustive against what is actually loaded, and the compiler-synthesized default arm throws.

</details>

**Q4.** Why does `Collectors.summingInt` share `IntStream.sum()`'s overflow trap while
`Collectors.averagingInt` does not?

<details><summary>Answer</summary>

`summingInt`'s internal accumulator is a single-element `int[1]` holding the running sum as an
`int`, so it wraps past `Integer.MAX_VALUE` exactly like a manual `int` accumulator would.
`averagingInt` accumulates into a two-element `long[2]` (sum, count) — its sum slot is a `long`,
so it does not overflow at the same magnitude. Use `summingLong` when the total could exceed
roughly two billion.

</details>

**Q5.** Name the release where `synchronized` stopped pinning a virtual thread, the JEP number,
and what still pins after that release.

<details><summary>Answer</summary>

Java 24, JEP 491 — object monitors became continuation-aware, so a virtual thread holding a
`synchronized` lock can now be unmounted from its carrier while blocked on I/O. Native and
foreign-frame calls (JNI, FFM) still pin at every release including 24, so
`jdk.VirtualThreadPinned` remains a live diagnostic, just with a narrower cause set.

</details>

**Q6.** A junior engineer says structured concurrency "is the same API since Java 19." What is
wrong with that, using the two shapes named in this file?

<details><summary>Answer</summary>

The Java 21 preview shape (JEP 453) uses public constructors (`new ShutdownOnFailure()`), `fork`
returning `Subtask<T>`, and two fixed policies (`ShutdownOnFailure`/`ShutdownOnSuccess`). Java 25
(JEP 505) replaces the constructors with static `open()` factories and replaces the two fixed
policies with a single composable `Joiner`. Code written against the 21 shape does not compile
against the 25 shape without changes — it is not source-stable across those releases, and as of
25 it is still only a preview, not final, on either shape.

</details>

**Q7.** What does Java 20 contribute to the language/API feature list, and what is the honest way
to answer "what shipped in 20" in an interview?

<details><summary>Answer</summary>

No language feature finalized in 20 — virtual threads, structured concurrency, record patterns
and pattern switch were all re-previewed, and scoped values entered incubator status. The honest
answer states that explicitly ("20 finalized nothing new — it re-previewed four features and
incubated a fifth") rather than guessing a feature from a neighboring release to avoid saying
"nothing."

</details>

**Q8.** Is `Object.finalize()` removed as of Java 25?

<details><summary>Answer</summary>

No. It was deprecated for removal at Java 18 (JEP 421) but has not been removed as of 25 — only a
compile-time deprecation warning applies. The exact release it will actually be removed in is
unresolved as of this file's date; do not state a specific future removal release as fact.

</details>

## Deferred

None.

## Open questions

- **Unverified:** the exact target release for structured concurrency's seventh preview round
  (JEP 533), which was still a draft proposal at the time this file was written — settle by
  checking the JEP's current target-release field on `openjdk.org`/`bugs.openjdk.org` once it is
  targeted.
- **Unverified:** the specific future release in which `Object.finalize()` will be fully removed —
  no removal JEP has a target release as of this file's date; settle by checking
  `bugs.openjdk.org` for a filed finalization-removal JEP.

---

**Leaves covered:** 3.16.1–3.16.22 (22 leaves)
**Leaves deferred:** none
**Diagrams included:** D-166, D-167
**Target version:** Java 21 LTS
**Lines:** 1029
