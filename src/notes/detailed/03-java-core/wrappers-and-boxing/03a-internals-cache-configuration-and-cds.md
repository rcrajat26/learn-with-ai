# 03 Java Core — Cache configuration and the CDS archive — INTERNALS (§3.4, 3.4.3, 3.4.4)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Boxing internals](03-internals-boxing.md) · Next: [The other wrapper caches](03b-internals-the-other-wrapper-caches.md)

`IntegerCache`'s static initializer is eleven lines long and delegates twice to code that does not live in `Integer.java`. This file is about those two delegations, and nothing else.

Assume everything the earlier files established. [`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md) built the model of a 256-entry array with a fixed `low` and a tunable `high`. [`01a2-the-archived-cache.md`](01a2-the-archived-cache.md) introduced the CDS archived subgraph at model level, along with `-Xshare`. And [`03-internals-boxing.md`](03-internals-boxing.md), the file immediately before this one, quoted the whole of `IntegerCache`, walked its five members, did the 256-entry and 5,136-byte arithmetic, and embedded D-102. None of that is repeated. What none of them opened up is the machinery on the far side of the two calls: `jdk.internal.misc.VM.getSavedProperty`, which is how a VM flag becomes a value that `java.lang` can read and application code cannot, and `jdk.internal.misc.CDS.initializeFromArchive`, which is how 256 objects arrive already built.

Everything below is measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**. Library source is quoted from that JDK's `lib/src.zip`, including `jdk/internal/misc/VM.java`, `jdk/internal/misc/CDS.java` and `java/lang/System.java`, which are the three files that between them explain the whole of the property path.

---

## 1. `VM.getSavedProperty`, and the knob you cannot read (3.4.3)

`[SOURCE]` `[RESEARCH]` The tuning value does not arrive as a system property, and by the time your `main` runs it is not one. It arrives as a VM flag; the VM translates it into a property in the raw startup property map; `System.initPhase1` hands that whole raw map to `VM.saveProperties` as a private snapshot, then builds the public `System.getProperties()` object from the same map **with this specific key deliberately dropped**. `IntegerCache` reads the snapshot. Your code reads the public object. The two disagree by design, and the disagreement is not an accident of timing — it is five lines of a `switch` in `System.java` naming the key.

### Why it exists

Two problems, and the property snapshot solves both.

The first is ordering. `IntegerCache` runs during `Integer`'s class initialization, which happens absurdly early — `Integer` is touched by the class loader, by the module system, by string encoding, by anything that autoboxes, and in practice before `System.props` is a fully-formed object at all. `System.getProperties()` returns a `java.util.Properties`, which is a Java-level `Hashtable` subclass that has to be constructed by Java code running on a working JVM. `IntegerCache` cannot wait for it. So the JDK gives `java.lang` a cheaper channel: a plain `Map<String, String>` handed straight in from the VM's native property initialization, before anything else exists.

The second is mutability. `System.setProperty` is public and callable at any time. If `IntegerCache` read the live property set, the cache's range would depend on *when the class was first touched* relative to whatever set the property — which is to say, on class-initialization order, which is not something an application controls. Two runs of the same program could get different `==` behaviour. Snapshotting at init level 0 and reading from the snapshot makes the range a property of the process, fixed before any application code exists.

Reach for this knob essentially never; the reasoning is in the concrete example below. Reach for `VM.getSavedProperty` in your own code never at all — it is in `jdk.internal.misc`, not exported to unnamed modules, and reading it requires `--add-exports`.

### The mechanism

The `high` half of `IntegerCache`'s static block, quoted from JDK 21.0.7:

```java
// high value may be configured by property
int h = 127;
String integerCacheHighPropValue =
    VM.getSavedProperty("java.lang.Integer.IntegerCache.high");
if (integerCacheHighPropValue != null) {
    try {
        h = Math.max(parseInt(integerCacheHighPropValue), 127);
        // Maximum array size is Integer.MAX_VALUE
        h = Math.min(h, Integer.MAX_VALUE - (-low) -1);
    } catch( NumberFormatException nfe) {
        // If the property cannot be parsed into an int, ignore it.
    }
}
high = h;
```

Line by line:

- `int h = 127;` — the JLS-mandated floor is the default, so an absent or unusable property leaves the cache at exactly the specified minimum.
- `VM.getSavedProperty(…)` — the snapshot read. Note this is the *only* configuration input to the class. There is no second path, no flag read, no native call.
- `if (… != null)` — absence is the common case and costs one null check.
- `Math.max(parseInt(prop), 127)` — the property can only **raise** `high`. A value below 127 is discarded silently. This is the JLS floor being enforced in code rather than trusted to the operator.
- `Math.min(h, Integer.MAX_VALUE - (-low) -1)` — the array-length clamp. `low` is `-128`, so `-low` is `128`, and the expression is `2147483647 - 128 - 1` = **2147483518**. That is the largest `high` the code will accept, chosen so that `size = (high - low) + 1` = `2147483518 + 128 + 1` = `2147483647` = `Integer.MAX_VALUE`, the largest possible array length. **Insight:** the clamp exists to stop `size` overflowing into a negative `int` and throwing `NegativeArraySizeException`, not to stop you doing something silly. An array at the clamp would be 2,147,483,647 references — 8.6 GB of `Object[]` before a single `Integer` is allocated. The code will happily try.
- `catch( NumberFormatException nfe)` with an empty body — an unparseable value is *ignored*, and `h` keeps whatever value it had when the throw happened. Since `parseInt` is the first thing in the `try`, that value is 127.

Now the far side. `jdk.internal.misc.VM`, quoted from JDK 21.0.7:

```java
/**
 * Returns the system property of the specified key saved at
 * system initialization time.  This method should only be used
 * for the system properties that are not changed during runtime.
 *
 * Note that the saved system properties do not include
 * the ones set by java.lang.VersionProps.init().
 */
public static String getSavedProperty(String key) {
    if (savedProps == null)
        throw new IllegalStateException("Not yet initialized");

    return savedProps.get(key);
}

private static Map<String, String> savedProps;

// Save a private copy of the system properties and remove
// the system properties that are not intended for public access.
//
// This method can only be invoked during system initialization.
public static void saveProperties(Map<String, String> props) {
    if (initLevel() != 0)
        throw new IllegalStateException("Wrong init level");

    // only main thread is running at this time, so savedProps and
    // its content will be correctly published to threads started later
    if (savedProps == null) {
        savedProps = props;
    }
```

What each piece establishes:

- `savedProps` is a bare `private static Map<String, String>` with **no `final`, no `volatile`, and no synchronization**. The comment says why that is safe rather than sloppy: `saveProperties` runs on the main thread before any other thread exists, so the write happens-before every later thread's start, and `Thread.start` is a happens-before edge under the memory model. This is the cheapest legal publication there is, and it is legal only because of *when* it runs.
- `getSavedProperty` throws `IllegalStateException("Not yet initialized")` if called before the snapshot lands. `IntegerCache` never sees that, because `System.initPhase1` calls `saveProperties` before it does almost anything else — but the throw is the reason you cannot simply move `getSavedProperty` earlier.
- `saveProperties` refuses to run unless `initLevel() != 0` is false. The init levels are named constants in the same file: `JAVA_LANG_SYSTEM_INITED = 1`, `MODULE_SYSTEM_INITED = 2`, `SYSTEM_LOADER_INITIALIZING = 3`, `SYSTEM_BOOTED = 4`, `SYSTEM_SHUTDOWN = 5`. Level 0 is "nothing yet". So the snapshot is taken at the earliest moment Java code runs at all.
- `if (savedProps == null)` — a second call is a no-op rather than an error, so the snapshot is genuinely write-once.

And the reason `System.getProperty` cannot see the key. `System.initPhase1`, quoted:

```java
Map<String, String> tempProps = SystemProps.initProperties();
VersionProps.init(tempProps);

// There are certain system configurations that may be controlled by
// VM options such as the maximum amount of direct memory and
// Integer cache size used to support the object identity semantics
// of autoboxing.  Typically, the library will obtain these values
// from the properties set by the VM.  If the properties are for
// internal implementation use only, these properties should be
// masked from the system properties.
//
// Save a private copy of the system properties object that
// can only be accessed by the internal implementation.
VM.saveProperties(tempProps);
props = createProperties(tempProps);
```

`tempProps` is the raw map. `VM.saveProperties(tempProps)` keeps a reference to it — the snapshot is the same object, not a copy, which is why the field is written rather than filled. `createProperties(tempProps)` then builds the public `Properties`, and this is the masking:

```java
private static Properties createProperties(Map<String, String> initialProps) {
    Properties properties = new Properties(initialProps.size());
    for (var entry : initialProps.entrySet()) {
        String prop = entry.getKey();
        switch (prop) {
            // Do not add private system properties to the Properties
            case "sun.nio.MaxDirectMemorySize":
            case "sun.nio.PageAlignDirectMemory":
                // used by java.lang.Integer.IntegerCache
            case "java.lang.Integer.IntegerCache.high":
                // used by sun.launcher.LauncherHelper
            case "sun.java.launcher.diag":
                // used by jdk.internal.loader.ClassLoaders
            case "jdk.boot.class.path.append":
                break;
            default:
                properties.put(prop, entry.getValue());
        }
    }
    return properties;
}
```

**Insight:** the key is invisible because it is named, in source, in a five-case fall-through `switch` whose `break` means "drop this entry". The JDK's own comment on the case is `// used by java.lang.Integer.IntegerCache`. This is not a lifecycle artefact and not a bug — the platform deliberately publishes the value to bootstrap code and withholds it from everyone else.

#### Measured behaviour of the two forms

Every row below was produced on JDK 21.0.7 by the same probe class, printing `Integer.valueOf(n) == Integer.valueOf(n)` for two values and `System.getProperty("java.lang.Integer.IntegerCache.high")`.

| Command-line | `valueOf(128) == valueOf(128)` | `valueOf(1000) == valueOf(1000)` | `System.getProperty(…)` |
|---|---|---|---|
| (none) | false | false | `null` |
| `-XX:AutoBoxCacheMax=1000` | true | **true** | `null` |
| `-Djava.lang.Integer.IntegerCache.high=1000` | true | **true** | `null` |
| `-XX:AutoBoxCacheMax=50` | false | false | `null` |
| `-XX:AutoBoxCacheMax=1000 -Djava…high=300` | true | **true** | `null` |
| `-XX:AutoBoxCacheMax=300 -Djava…high=1000` | true | **false** | `null` |
| `-Djava.lang.Integer.IntegerCache.high=banana` | false | false | `null` |

Read the rows:

- Rows 2 and 3 are the headline: **both forms work, and neither is readable.** `-XX:+PrintFlagsFinal -version` prints exactly `intx AutoBoxCacheMax                          = 128                                    {C2 product} {default}`, so the flag's default is 128 while the cache's default `high` is 127 — the flag is an exclusive upper bound in spirit, and `AutoBoxCacheMax=128` produces the same 256-entry cache as no flag at all.
- Row 4 is the `Math.max` in action. `-XX:AutoBoxCacheMax=50` changes **nothing**: 127 still interns, 128 still does not. The knob is one-directional. `low` cannot be moved at all — it is `static final int low = -128`, a compile-time constant with no property read anywhere near it.
- Rows 5 and 6 settle the "two paths or one" question by measurement. With both set, **the `-XX` flag wins in both directions**: `XX=1000, D=300` gives a cache reaching 1000, and `XX=300, D=1000` gives one that stops before 1000. If these were independent paths the larger value would win, or the property would win in one case and the flag in the other. Since `IntegerCache`'s source reads only the property, the only consistent explanation is that the VM writes `java.lang.Integer.IntegerCache.high` into the startup property map from the flag, **overwriting** any `-D` the user supplied. There is one path, and the flag is a front end to it. **Unverified:** the exact HotSpot call site that performs the write was not read (see `## Open questions`); the direction of precedence, however, is measured.
- Row 7 is the swallowed exception. `banana` reaches `parseInt`, throws `NumberFormatException`, the empty `catch` discards it, and `high` stays 127 — silently, with no warning on stderr and a zero exit status. The `-XX` form of the same mistake behaves completely differently: `-XX:AutoBoxCacheMax=banana` is rejected by the launcher before any Java runs, with `Improperly specified VM option 'AutoBoxCacheMax=banana'` followed by `Error: Could not create the Java Virtual Machine.` So the flag fails loudly and the property fails silently. **Insight:** that asymmetry is a direct consequence of there being one path with two front doors — the flag is validated as an `intx` by HotSpot's option parser, the property is validated by `Integer.parseInt` inside a `catch` block that was written to ignore it.

`HotSpotDiagnosticMXBean` does expose the flag, measured:

| Command-line | `getVMOption("AutoBoxCacheMax")` value / origin | actual cache reaches 1000? |
|---|---|---|
| (none) | `128` / `DEFAULT` | no |
| `-XX:AutoBoxCacheMax=1000` | `1000` / `VM_CREATION` | yes |
| `-Djava.lang.Integer.IntegerCache.high=1000` | `128` / `DEFAULT` | **yes** |

The MXBean reads the *flag*, not the effective cache range, so the third row is a false negative: the cache reaches 1000 and the bean says 128. It is a better diagnostic than `System.getProperty` (which is `null` in all three rows and therefore carries no information at all), but it is still not the answer to "what is the cache range".

#### The `{C2 product}` categorisation

`{C2 product}` in the `PrintFlagsFinal` output means the flag is declared in C2's flag table (`c2_globals.hpp`), not that C2 is the only consumer. The same run reports a distinct, separately-named flag: `bool EliminateAutoBox = true {C2 product} {default}` — that one is unambiguously C2's box-elimination switch. **Unverified:** whether C2 *itself* consumes `AutoBoxCacheMax`'s value when reasoning about box identity, or whether the flag's only effect is the startup property write, was not established — HotSpot's C++ source was not available in this environment. Recorded in `## Open questions`. Do not repeat the common claim that "it is a C2 flag, so C2 uses it"; the categorisation does not say that.

### Diagram

No diagram of its own: the picture for the cache's shape and index arithmetic is **D-102**, embedded in [`03-internals-boxing.md`](03-internals-boxing.md), and everything in this concept is a change to the single value `high` that sizes it.

### A concrete example

`FundsLedger` writes positions keyed by a numeric position code. The codes for the client-facing buckets and their reconciliation counterparts sit in a dense block in the low thousands — 1000 through 1128 — and the write path boxes the code once per ledger entry to put it in a `List<Integer>` for the batch writer. At 2.8M stake reservations a day this is 2.8M boxes.

```java
public final class FundsLedgerBatch {

    private final List<Integer> positionCodes;

    public FundsLedgerBatch(int expectedEntries) {
        this.positionCodes = new ArrayList<>(expectedEntries);
    }

    public void record(Movement movement) {
        positionCodes.add(movement.positionCode());   // boxes: 1000..1128
    }

    public int size() {
        return positionCodes.size();
    }
}
```

Measured with `com.sun.management.ThreadMXBean.getThreadAllocatedBytes` around a loop of 2,800,000 `record` calls cycling codes 1000 through 1128, with the `ArrayList` presized so the backing array is allocated before the measurement window opens:

| Run | Bytes allocated in the loop | Per element | `valueOf(1128) == valueOf(1128)` |
|---|---|---|---|
| default | **44,801,176** | 16.00042 | false |
| `-XX:AutoBoxCacheMax=1128` | **1,176** | 0.00042 | true |

44,801,176 bytes is 2,800,000 × 16 plus a 1,176-byte residue from the measurement harness itself. 16 is one `Integer` per element: a 12-byte header plus a 4-byte `int`, already a multiple of the 8-byte object alignment. With the cache raised past 1128 the loop allocates the same 1,176-byte residue and nothing else — every `add` returns a pre-existing cached instance, and the 4 bytes per element of compressed reference in the backing array were already paid for by the presizing. The flag works, and it works completely.

Do not use it. The alternative that does not touch a global JVM flag:

```java
public final class FundsLedgerBatch {

    // Dense codes 1000..1128 -> a primitive array. No boxing, no flag, no shared identity.
    private static final int CODE_BASE = 1000;
    private final int[] positionCodes;
    private int count;

    public FundsLedgerBatch(int expectedEntries) {
        this.positionCodes = new int[expectedEntries];
    }

    public void record(Movement movement) {
        positionCodes[count++] = movement.positionCode() - CODE_BASE;
    }

    public IntStream codes() {
        return Arrays.stream(positionCodes, 0, count).map(c -> c + CODE_BASE);
    }
}
```

4 bytes per element, measured as 11,200,712 bytes for an `int[]` of 2,800,000 — a quarter of the boxed cost and a quarter of what the raised cache saves you in *references* alone. Where the code is genuinely an enumeration rather than a number, the same idea with type safety is an `EnumMap` or `EnumSet`, both of which are arrays and bit vectors underneath rather than hashed structures; that mechanism is [`../enums/03c-internals-enumset-enummap.md`](../enums/03c-internals-enumset-enummap.md).

The recommendation is the primitive array, and the reason is blast radius. Raising `AutoBoxCacheMax` changes `Integer` identity **process-wide, for every library in the JVM**. Jackson, Hibernate, the Spring context, the JDBC driver, the metrics client and every transitive dependency all get a different `==` answer for values between 128 and your new bound, and none of them were tested that way. You are making a global semantic change to fix a local allocation problem in one class, and the local fix is cheaper anyway.

### The gotcha

The flag lives in the startup script — `JAVA_OPTS`, a Dockerfile `ENTRYPOINT`, a Kubernetes `JAVA_TOOL_OPTIONS` — and the test suite does not have it. Surefire forks its own JVM with its own argument list. So `Integer.valueOf(1000) == Integer.valueOf(1000)` is `false` under `mvn test` and `true` in production, and any code that compares boxed ledger codes with `==` has two different behaviours. Which way round the bug bites depends on which behaviour the code accidentally relies on, and both directions happen: an `==` comparison that passes its tests and fails in production (values now shared where the test expected distinct objects is harmless; the reverse is not), and an `==` comparison that fails its tests and works in production, which gets "fixed" by adding the flag to the test JVM. The second is worse, because it makes the environments agree while leaving the bug in place.

**Interview:** *How would you change the `Integer` cache range, and what breaks?* Two forms, one path: `-XX:AutoBoxCacheMax=N` or `-Djava.lang.Integer.IntegerCache.high=N`, and the flag overrides the property when both are set. `Math.max(parseInt(prop), 127)` means it can only raise the bound, never lower it, and `low` is a compile-time constant at −128 that cannot move. Then say you would not do it: it changes `==` semantics process-wide for every library in the JVM, it is unreadable via `System.getProperty` so nothing can assert it was applied, and on Java 21 it silently discards the CDS archived cache. Fix the boxing locally with a primitive array or an `EnumMap` instead.

> **Definition.** `java.lang.Integer.IntegerCache.high` is a private startup property, written by the VM from `-XX:AutoBoxCacheMax` or from `-D`, snapshotted into `VM.savedProps` at init level 0, masked out of the public `Properties` by name in `System.createProperties`, and read exactly once by `IntegerCache`'s static initializer, where `Math.max` allows it only to raise `high` above 127.

---

## 2. `CDS.initializeFromArchive` and the archived heap subgraph (3.4.4)

`[SOURCE]` `[RESEARCH]` The 256 `Integer` objects in the default cache are byte-identical on every JVM start: same values, same layout, no external references. So they are written into the CDS archive file once, at archive dump time, and on every subsequent start the JVM **memory-maps them back** as a region of the Java heap. `IntegerCache`'s static block then runs, calls `CDS.initializeFromArchive`, finds that `archivedCache` has already been filled in by native code, and skips its own loop entirely. This is not a cache of the cache. The objects the mapped array points at are the same objects `valueOf` will return — they were simply never allocated by this process.

### Why it exists

Startup time. `IntegerCache` is one member of a set of archived subgraphs, and the measured `-Xlog:cds+heap=info` output on a default JDK 21.0.7 start lists the wrapper caches together:

```
[0.008s][info][cds,heap] Patching native pointers in heap region
[0.009s][info][cds,heap] resolve subgraph java.lang.Integer$IntegerCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Long$LongCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Byte$ByteCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Short$ShortCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Character$CharacterCache
[0.015s][info][cds,heap] init subgraph java.lang.Integer$IntegerCache
[0.015s][info][cds,heap] initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x000000c800036b28 (early)
[0.022s][info][cds,heap] init subgraph java.lang.Long$LongCache
[0.022s][info][cds,heap] initialize_from_archived_subgraph java.lang.Long$LongCache 0x000000c800039a30
```

Four of the five wrapper caches are 256 entries and `Character`'s is 128, so the aggregate is 1,152 objects plus five arrays that no longer need constructing — and, more to the point, five static initializers that no longer need to *run* a loop. Note there is no `Boolean` subgraph: `Boolean` has no cache class, only `TRUE` and `FALSE`.

The second, less obvious benefit: **mapped objects are not allocated in Eden.** A constructed cache puts 256 short-lived-looking `Integer` objects into the young generation, where they survive every young collection forever and get copied through the survivor spaces until they are tenured. Mapped objects start life outside that machinery entirely. For one cache the effect is a rounding error; for the whole archived subgraph set, plus archived `String` literals and archived immutable collections, it is measurable.

Reach for `-Xshare:off` only as a diagnostic, and know that it changes which of the three code paths below you are on. There is no reason to disable it in production.

### The mechanism

The CDS half of `IntegerCache`'s static block, quoted from JDK 21.0.7:

```java
// Load IntegerCache.archivedCache from archive, if possible
CDS.initializeFromArchive(IntegerCache.class);
int size = (high - low) + 1;

// Use the archived cache if it exists and is large enough
if (archivedCache == null || size > archivedCache.length) {
    Integer[] c = new Integer[size];
    int j = low;
    for(int i = 0; i < c.length; i++) {
        c[i] = new Integer(j++);
    }
    archivedCache = c;
}
cache = archivedCache;
```

And the method it calls, quoted from `jdk.internal.misc.CDS`:

```java
/**
 * Initialize archived static fields in the given Class using archived
 * values from CDS dump time. Also initialize the classes of objects in
 * the archived graph referenced by those fields.
 *
 * Those static fields remain as uninitialized if there is no mapped CDS
 * java heap data or there is any error during initialization of the
 * object class in the archived graph.
 */
public static native void initializeFromArchive(Class<?> c);
```

It is `native`, and that is the end of what Java source can tell you. There is no body to read: the implementation is in HotSpot's C++, in the shared-heap code (`heapShared.cpp` and the `cdsHeap` support around it), which was **not available in this environment** — so nothing below is a claim about how the C++ works, only about what it demonstrably does. The javadoc is the contract, and two clauses of it matter: *"Initialize archived **static fields** in the given Class"* — so it writes fields reflectively-but-natively, by name, from the archive; and *"Those static fields remain as uninitialized if there is no mapped CDS java heap data"* — so failure is silent and leaves the field at its default value, `null`.

That contract is what makes the Java side read the way it does.

#### Two decision points, three outcomes

Every earlier file simplified this into "either it uses the archive or it builds the array". There are two independent decisions:

1. **Inside `initializeFromArchive`**, in native code: is a mapped heap subgraph for `IntegerCache` present? If yes, `archivedCache` is written to point at the archived `Integer[]`. If no, nothing is written and `archivedCache` stays `null`. The call itself is **unconditional** — the Java code does not ask whether CDS is enabled before calling, it just calls and inspects the result. `CDS.isSharingEnabled()` exists in the same class and is deliberately not used here.
2. **In the `if`**, in Java: `archivedCache == null || size > archivedCache.length`. Two ways to fail into the constructing branch.

Which gives three outcomes:

| `archivedCache` after the native call | `size` versus `archivedCache.length` | Outcome | `cache` points at |
|---|---|---|---|
| non-`null` (subgraph mapped) | `size <= length` | archive used as-is; loop never runs | the mapped array |
| non-`null` (subgraph mapped) | `size > length` | subgraph mapped **and then discarded**; loop runs | a freshly constructed array |
| `null` (no mapped data) | not evaluated (short-circuit) | loop runs | a freshly constructed array |

The middle row is the interesting one and it is measured. With `-XX:AutoBoxCacheMax=1000`, the log still shows the subgraph being resolved and initialized:

```
[0.014s][info][cds,heap] resolve subgraph java.lang.Integer$IntegerCache
[0.014s][info][cds,heap] init subgraph java.lang.Integer$IntegerCache
[0.014s][info][cds,heap] initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x0000007000036b28 (early)
```

— the archive is read, the objects are mapped, `archivedCache` is written — and then `size` = `(1000 - (-128)) + 1` = **1129**, which is greater than `archivedCache.length` = **256**, so the `if` body runs and builds 1,129 new `Integer` objects, and `archivedCache = c` overwrites the reference to the mapped array with the constructed one.

**Insight:** raising the tuning flag silently costs you the archive. You pay the mapping work *and* the construction work, and the mapped 256 objects become immediately unreachable garbage. The tuning knob and the startup optimisation are in direct conflict, and nothing tells you. The arithmetic for the price: 1,129 `Integer` objects at 16 bytes each is 18,064 bytes, plus a 1,129-element `Integer[]` at 16 bytes of header plus 1,129 × 4 bytes of compressed reference = 4,532, rounded up to the 8-byte alignment = 4,536. Total **22,600 bytes** constructed at startup, replacing a 5,136-byte mapped array (256 × 16 = 4,096, plus 16 + 256 × 4 = 1,040) that you also paid to map.

With `-Xshare:off`, measured: **zero lines** matching `cds,heap` in a full `-Xlog:cds+heap=info` run. The archive is not consulted at all, `archivedCache` stays `null`, and the loop constructs all 256 objects — the third row of the table.

#### Two things worth measuring rather than asserting

**The mapped addresses.** The address printed on the `initialize_from_archived_subgraph` line is not stable across runs, but it is not random either. Two runs of the same program printed `0x000000c800036b28` and `0x0000007000036b28`. The high bits differ — the archive's mapping base is randomised, as any mapped region's is — and the low bits `36b28` are **identical**. The offset of the `IntegerCache` subgraph within the archived heap region is fixed at dump time, which is exactly what "byte-identical on every start" means in practice: the same bytes at the same offset, at a different base.

**Whether archived objects are identity-distinguishable from constructed ones.** `System.identityHashCode(Integer.valueOf(0))`, measured as the first identity hash requested in the process:

| Run | `identityHashCode(Integer.valueOf(0))` |
|---|---|
| default (`-Xshare:auto`) | 692404036 |
| `-Xshare:auto` explicit | 692404036 |
| default, repeated | 692404036 |
| `-Xshare:off` | 1450821318 |
| `-Xshare:off`, repeated | 1450821318 |
| `-XX:AutoBoxCacheMax=1000` (subgraph discarded) | 692404036 |

The values are perfectly reproducible within a configuration and differ between the archived and non-archived configurations. That is a real, repeatable difference. It is **not** evidence that the hash encodes the address, and the address measurement above proves it cannot: the address's high bits change from run to run while the hash does not. **Unverified:** two explanations fit — the archive may carry a pre-computed identity hash in the archived object's mark word, or HotSpot's identity-hash PRNG may simply be deterministic per configuration and consume a different number of values before `main` on the two paths. The `AutoBoxCacheMax=1000` row, where the object returned by `valueOf(0)` is freshly constructed and yet the hash matches the archived runs, points at the second explanation. Recorded in `## Open questions`. Do not tell an interviewer you can detect an archived object by its identity hash.

**The `(early)` marker.** It appears on the `Integer$IntegerCache` line and not on `Long$LongCache`, in every run. `CDS.java` on JDK 21.0.7 does **not** distinguish early from non-early initialisation — `initializeFromArchive` has exactly one form and no flag parameter — so the distinction is entirely on the HotSpot side and cannot be settled from Java source. **Unverified**, recorded in `## Open questions`.

#### Why `archivedCache` is the only non-`final` field

`IntegerCache` declares:

```java
@Stable
static final Integer[] cache;
static Integer[] archivedCache;
```

`archivedCache` has no `final` because native code writes it from outside any `<clinit>`, and the JVM's field-modification checks would reject a store to a `final` static outside its own class initializer. `cache` keeps its `final` and its `@Stable`, and is assigned exactly once, at the end of the block, by `cache = archivedCache`.

**Insight:** that last line is the design goal. After it, `cache` points at either the mapped array or the constructed one, and `Integer.valueOf` — which reads `IntegerCache.cache[i + (-IntegerCache.low)]` and nothing else — cannot tell which. The archived path is invisible to the API. It is also invisible to the JIT in the way that matters: `@Stable` on `cache` licenses C2 to treat the field and its elements as constants after initialization regardless of which array it ended up pointing at.

### Diagram

No diagram of its own: **D-102**, embedded in [`03-internals-boxing.md`](03-internals-boxing.md), is the picture of the array and the index arithmetic, and the whole point of this concept is that the picture is identical whether the array was mapped or constructed.

### A concrete example

An observation harness. This is a complete class plus the exact command lines that put the JVM on each of the three outcomes, with the real captured output.

```java
public class CachePathProbe {

    public static void main(String[] args) {
        // Ledger position codes: the default cache covers none of 1000..1128.
        System.out.println("valueOf(1000)==valueOf(1000) : "
                + (Integer.valueOf(1000) == Integer.valueOf(1000)));
        System.out.println("valueOf(127)==valueOf(127)   : "
                + (Integer.valueOf(127) == Integer.valueOf(127)));
        System.out.println("valueOf(128)==valueOf(128)   : "
                + (Integer.valueOf(128) == Integer.valueOf(128)));
        System.out.println("System.getProperty(high)     : "
                + System.getProperty("java.lang.Integer.IntegerCache.high"));
        System.out.println("identityHashCode(valueOf(0)) : "
                + System.identityHashCode(Integer.valueOf(0)));
    }
}
```

Compile once:

```
javac -d /tmp/probe CachePathProbe.java
```

**Outcome 1 — archived, used as-is.** The default. `-Xshare:auto` needs no flag:

```
java -Xlog:cds+heap=info -cp /tmp/probe CachePathProbe
```

```
[0.007s][info][cds,heap] Patching native pointers in heap region
[0.008s][info][cds,heap] resolve subgraph java.lang.Integer$IntegerCache
[0.013s][info][cds,heap] init subgraph java.lang.Integer$IntegerCache
[0.013s][info][cds,heap] initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x000000f800036b28 (early)
valueOf(1000)==valueOf(1000) : false
valueOf(127)==valueOf(127)   : true
valueOf(128)==valueOf(128)   : false
System.getProperty(high)     : null
identityHashCode(valueOf(0)) : 692404036
```

**Outcome 2 — no mapped data, constructed.**

```
java -Xshare:off -Xlog:cds+heap=info -cp /tmp/probe CachePathProbe
```

```
valueOf(1000)==valueOf(1000) : false
valueOf(127)==valueOf(127)   : true
valueOf(128)==valueOf(128)   : false
System.getProperty(high)     : null
identityHashCode(valueOf(0)) : 1450821318
```

Not one `cds,heap` line: the log level is set and the log is silent, which is the evidence that the archive was never consulted. The `==` results are identical to outcome 1, which is the point — the two paths are behaviourally indistinguishable through the API.

**Outcome 3 — mapped, then discarded and rebuilt.**

```
java -XX:AutoBoxCacheMax=1000 -Xlog:cds+heap=info -cp /tmp/probe CachePathProbe
```

```
[0.007s][info][cds,heap] resolve subgraph java.lang.Integer$IntegerCache
[0.014s][info][cds,heap] init subgraph java.lang.Integer$IntegerCache
[0.014s][info][cds,heap] initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x0000007000036b28 (early)
valueOf(1000)==valueOf(1000) : true
valueOf(128)==valueOf(128)   : true
System.getProperty(high)     : null
identityHashCode(valueOf(0)) : 692404036
```

The subgraph initialises — the three log lines are the same as outcome 1 — and `valueOf(1000) == valueOf(1000)` is `true`, which is only possible if the 1,129-element array was built by the loop. Both facts in one run: the archive was read and the archive was thrown away.

### The gotcha

Treating CDS as a developer opt-in. It is not: the default archive `classes.jsa` ships inside the JDK image, `-Xshare:auto` is the default sharing mode, and no configuration is required to get the archived path. So on Java 21 **the archived path is what almost every process actually takes**, and "the static block constructs 256 `Integer` objects at class-initialization time" is the *uncommon* case — it happens only under `-Xshare:off`, or on a JDK image whose archive is missing or mismatched, or when the tuning flag has pushed `size` past 256.

**[VERSION-TRAP]** Older material — and most blog explanations of `IntegerCache` — describes only the loop, because that was the whole story before archived heap objects existed. Archived heap subgraphs arrived for the wrapper caches in JDK 9-era CDS work and the `archivedCache` field is not present in JDK 8's `Integer.java` at all. What is true in Java 21: the field exists, `CDS.initializeFromArchive` is called unconditionally on every start, and by default it succeeds. What used to be true, and what an interviewer may be expecting: the static block allocates all 256 objects itself. Give the 21 answer and name the older one, because "the static block builds the array" as a bare statement is now a version-stale answer.

**Interview:** *What does `CDS.initializeFromArchive` do in `IntegerCache`?* It is a `native` method that, if a mapped CDS heap subgraph for `IntegerCache` exists, writes the class's archived static field `archivedCache` to point at the archived `Integer[]`; if there is no mapped data it silently leaves the field `null`. It is called unconditionally, so the Java code that follows inspects the result rather than the configuration: `archivedCache == null || size > archivedCache.length` decides whether to construct. That gives three outcomes — archive used, archive mapped then discarded because the tuning flag made `size` too big, and no archive at all under `-Xshare:off`. `cache = archivedCache` at the end means `valueOf` cannot tell the difference.

> **Definition.** `CDS.initializeFromArchive(IntegerCache.class)` is an unconditional `native` call that populates `IntegerCache.archivedCache` from a memory-mapped CDS heap subgraph when one is present and leaves it `null` when it is not, so that on a default Java 21 start the 256 cached `Integer` objects are mapped from the archive rather than allocated, indistinguishably to `Integer.valueOf`.

---

## Pitfalls

### Reading the tuning flag with `System.getProperty` and concluding it was not applied

**Wrong**

```java
@Component
public class BoxingCacheHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        String high = System.getProperty("java.lang.Integer.IntegerCache.high");
        return high == null
                ? Health.down().withDetail("integerCacheHigh", "not configured").build()
                : Health.up().withDetail("integerCacheHigh", high).build();
    }
}
```

Measured on JDK 21.0.7 with `-XX:AutoBoxCacheMax=1000` on the command line: the endpoint reports `not configured`, and `Integer.valueOf(1000) == Integer.valueOf(1000)` is `true` in the same process. The flag was applied. The property is masked out of the public `Properties` by name in `System.createProperties`, so it is `null` in every configuration — with the flag, with the `-D` form, and without either.

**Right**

Assert the behaviour, not the configuration:

```java
@Component
public class BoxingCacheHealthIndicator implements HealthIndicator {

    // The only reliable probe is identity itself.
    private static int measureCacheHigh() {
        int probe = 127;
        while (probe < Integer.MAX_VALUE - 1
                && Integer.valueOf(probe + 1) == Integer.valueOf(probe + 1)) {
            probe++;
        }
        return probe;
    }

    @Override
    public Health health() {
        return Health.up().withDetail("integerCacheHigh", measureCacheHigh()).build();
    }
}
```

`HotSpotDiagnosticMXBean.getVMOption("AutoBoxCacheMax")` is a partial alternative — measured, it does return `1000` with origin `VM_CREATION` when the `-XX` flag is set, and `128` with origin `DEFAULT` when it is not. But measured with the `-D` form instead, it reports `128` / `DEFAULT` while the cache genuinely reaches 1000, so it answers "was the flag set" and not "what is the cache range". Use it for the first question only.

**Why people believe it:** the tunable is documented and discussed everywhere as a system property, its name is a system-property name, and `-D` genuinely sets it. Every other `-D` you pass is readable through `System.getProperty`, so nothing suggests this one is deliberately removed — and the removal is invisible unless you read `System.createProperties`.

### Setting `-XX:AutoBoxCacheMax` in production to reduce allocation

**Wrong**

```
# JAVA_OPTS in the FundsLedger deployment
-Xmx6g -XX:AutoBoxCacheMax=1128
```

The measured allocation win on the batch path is real: 44,801,176 bytes down to 1,176 for 2,800,000 boxed position codes. Two costs are not measured by the person who added the flag. First, the CDS archived subgraph is mapped and then discarded, because `size` = `(1128 + 128) + 1` = **1257** exceeds `archivedCache.length` = 256, so startup pays both the mapping and the construction of 1,257 `Integer` objects plus a 1,257-element array. Second, `==` now returns `true` for every `Integer` pair between 128 and 1128 in *every library in the process* — the JSON mapper, the ORM, the connection pool, the metrics client — none of which were tested under that identity regime.

**Right**

Fix the boxing where it happens:

```java
private static final int CODE_BASE = 1000;
private final int[] positionCodes = new int[expectedEntries];

public void record(Movement movement) {
    positionCodes[count++] = movement.positionCode() - CODE_BASE;
}
```

Measured: an `int[]` of 2,800,000 is 11,200,712 bytes, 4.000 per element — a quarter of the boxed cost, and better than the raised-cache version once the backing `Object[]`'s 4 bytes per reference are counted. No JVM flag, no change to any other library's semantics, no cost to startup, and the win is visible in the code rather than in a deployment script.

**Why people believe it:** the flag is the only knob in the JVM that directly addresses boxing allocation, the measurement it produces is dramatic and easy to reproduce, and both of its costs are invisible — the CDS interaction produces no warning and the identity change produces no error, only a different answer to `==` somewhere else in the process.

### Assuming the constructed path is the normal one

**Wrong**

```java
// A unit test that "documents" the cache's construction cost.
@Test
void integerCacheAllocatesTwoHundredFiftySixObjectsAtStartup() {
    long before = allocatedBytes();
    Class.forName("java.lang.Integer");     // force <clinit>
    long after = allocatedBytes();
    assertThat(after - before).isEqualTo(5136);   // 256*16 + array
}
```

The assertion is wrong twice. `Integer` has certainly been initialized long before any test method runs, so the `<clinit>` will not fire at all. And even in a fresh JVM on a default Java 21 start, the 256 objects are not allocated: measured, `-Xlog:cds+heap=info` shows `initialize_from_archived_subgraph java.lang.Integer$IntegerCache` and the loop in the static block never executes. The 5,136-byte figure is the *size of the mapped region*, not an allocation the process performs.

**Right**

If the question is which path a given JVM took, ask the JVM:

```
java -Xlog:cds+heap=info -version 2>&1 | grep 'java.lang.Integer\$IntegerCache'
```

Measured, this prints three lines on a default start (`resolve subgraph`, `init subgraph`, `initialize_from_archived_subgraph`) and **nothing at all** under `-Xshare:off`. That is a direct observation of the branch taken, which no in-process assertion can give you, because `cache = archivedCache` makes the two outcomes indistinguishable from Java.

**Why people believe it:** the static block is right there in the source and the loop is the only part of it that obviously does work, so the loop reads as the mechanism and `CDS.initializeFromArchive` reads as an optimisation you would have to enable. It is the reverse: the call is unconditional and, by default, the loop is dead code.

### Expecting an invalid tuning value to fail loudly

**Wrong**

```
# A typo, or a value templated in from an empty config variable.
-Djava.lang.Integer.IntegerCache.high=banana
```

Measured on JDK 21.0.7: the JVM starts normally, exit status 0, nothing on stderr, and the cache boundary is exactly the default — `valueOf(127) == valueOf(127)` is `true`, `valueOf(128) == valueOf(128)` is `false`. `parseInt("banana")` throws `NumberFormatException` inside the `try`, the `catch` block is empty with the comment `// If the property cannot be parsed into an int, ignore it.`, and `h` is still 127 from its initialization. The same class of typo in a value that *does* parse is worse: `-Djava…high=50` also silently produces the default cache, because `Math.max(50, 127)` is 127.

**Right**

Use the `-XX` form, which is validated by HotSpot's option parser before any Java runs. Measured, `-XX:AutoBoxCacheMax=banana` refuses to start:

```
Improperly specified VM option 'AutoBoxCacheMax=banana'
Error: Could not create the Java Virtual Machine.
Error: A fatal exception has occurred. Program will exit.
```

A non-zero exit at startup is a deployment failure you will see. And if you are setting the value at all, assert the resulting behaviour on the way up rather than trusting the flag:

```java
private static void requireCacheReaches(int expectedHigh) {
    if (Integer.valueOf(expectedHigh) != Integer.valueOf(expectedHigh)) {
        throw new IllegalStateException(
                "Integer cache does not reach " + expectedHigh
                + "; check -XX:AutoBoxCacheMax on this JVM");
    }
}
```

**Why people believe it:** every other JVM configuration mistake is loud. A bad `-XX` flag refuses to boot, a bad `-Xmx` refuses to boot, a malformed `-javaagent` refuses to boot. The property form is the one place where a startup-critical value is parsed by ordinary library code inside a `catch` block that was written to be permissive, and permissiveness there is indistinguishable from the value being absent.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Property name | `java.lang.Integer.IntegerCache.high` |
| Flag name | `-XX:AutoBoxCacheMax` |
| Flag default | `128`, printed as `intx AutoBoxCacheMax = 128 {C2 product} {default}` |
| Cache `high` default | `127` (the JLS floor), so flag `128` and no flag give the same cache |
| Number of configuration paths | **one** — the property; the flag is a front end that writes it |
| Precedence when both set | the `-XX` flag wins, measured in both directions |
| Direction of change | raise only; `Math.max(parseInt(prop), 127)` |
| Can `low` be changed? | no — `static final int low = -128`, no property read |
| `Math.min` clamp | `Integer.MAX_VALUE - (-low) - 1` = `2147483647 - 128 - 1` = **2147483518** |
| Why the clamp exists | to keep `size = (high - low) + 1` from exceeding `Integer.MAX_VALUE` |
| Unparseable property value | silently ignored, `high` stays 127; empty `catch (NumberFormatException)` |
| Unparseable `-XX` value | JVM refuses to start: `Improperly specified VM option` |
| Value below 127 | silently ignored by `Math.max` |
| `System.getProperty("java.lang.Integer.IntegerCache.high")` | **always `null`** |
| Why it is `null` | masked by name in `System.createProperties`'s five-case `switch` |
| Snapshot holder | `jdk.internal.misc.VM.savedProps`, a plain non-`final` `Map<String, String>` |
| Snapshot taken at | `System.initPhase1`, via `VM.saveProperties(tempProps)`, at init level 0 |
| `getSavedProperty` before the snapshot | `IllegalStateException("Not yet initialized")` |
| `saveProperties` at a later level | `IllegalStateException("Wrong init level")` |
| Init levels | 1 `JAVA_LANG_SYSTEM_INITED`, 2 `MODULE_SYSTEM_INITED`, 3 `SYSTEM_LOADER_INITIALIZING`, 4 `SYSTEM_BOOTED`, 5 `SYSTEM_SHUTDOWN` |
| `HotSpotDiagnosticMXBean.getVMOption("AutoBoxCacheMax")` | reports the flag (`1000` / `VM_CREATION`), not the cache; blind to the `-D` form |
| CDS call | `CDS.initializeFromArchive(IntegerCache.class)`, `public static native void` |
| Called conditionally? | no — **unconditional**; the Java code inspects the result |
| On no mapped data | `archivedCache` left `null`, silently |
| The deciding test | `archivedCache == null \|\| size > archivedCache.length` |
| Outcomes | three: archive used, archive mapped then discarded, no archive |
| `Long`/`Byte`/`Short`/`Character` test | `archivedCache.length != size`, not `>` |
| Archive discarded when | `size > 256`, i.e. any raised `high` |
| Cost of that discard at `high` = 1000 | `size` = 1129; 1,129 × 16 + 4,536 = **22,600 bytes** built at startup |
| Default sharing mode | `-Xshare:auto`, so the archived path is the normal one |
| `-Xshare:off` | zero `cds,heap` log lines; loop constructs 256 objects |
| Log switch | `-Xlog:cds+heap=info` |
| Archived wrapper subgraphs | `Integer`, `Long`, `Byte`, `Short`, `Character` — **no `Boolean`** |
| `(early)` marker | on `Integer$IntegerCache`, not on `Long$LongCache`; meaning unverified |
| Mapped address stability | low bits fixed (`36b28`), base randomised per run |
| Why `archivedCache` is not `final` | native code writes it from outside `<clinit>` |
| Why `cache` stays `final` + `@Stable` | assigned once by `cache = archivedCache`; JIT treats it as constant |
| Boxed 2.8M position codes 1000–1128, default | 44,801,176 bytes, 16.00042 per element |
| Same, with `-XX:AutoBoxCacheMax=1128` | 1,176 bytes total |
| Same as `int[]` | 11,200,712 bytes, 4.000 per element |

## Self-test

**Q1.** A colleague sets `-XX:AutoBoxCacheMax=1000` and then adds a startup log line reading `System.getProperty("java.lang.Integer.IntegerCache.high")`. It logs `null`. Did the flag work?

<details><summary>Answer</summary>

Yes. Measured on JDK 21.0.7, with that flag set, `Integer.valueOf(1000) == Integer.valueOf(1000)` is `true` and `System.getProperty("java.lang.Integer.IntegerCache.high")` is `null` in the same process. The property is deliberately masked: `System.initPhase1` hands the raw startup property map to `VM.saveProperties`, which keeps it as the private `savedProps` snapshot that `IntegerCache` reads, and then calls `System.createProperties` to build the public `Properties` from the same map. `createProperties` contains a five-case fall-through `switch` that drops specific keys, and `"java.lang.Integer.IntegerCache.high"` is one of them, carrying the JDK's own comment `// used by java.lang.Integer.IntegerCache`. So the value is readable only through `jdk.internal.misc.VM.getSavedProperty`, and it is `null` from `System.getProperty` in every configuration. To check whether the flag took effect, assert the behaviour — `Integer.valueOf(n) == Integer.valueOf(n)` — or read `HotSpotDiagnosticMXBean.getVMOption("AutoBoxCacheMax")`, remembering that the bean reports the flag and is blind to the `-D` form.

</details>

**Q2.** `-XX:AutoBoxCacheMax=300` and `-Djava.lang.Integer.IntegerCache.high=1000` are both on the command line. What is `high`, and what does the answer tell you about the architecture?

<details><summary>Answer</summary>

Measured: `high` ends up at 300 — `Integer.valueOf(1000) == Integer.valueOf(1000)` is `false` while `valueOf(128) == valueOf(128)` is `true`. The reverse combination, `-XX:AutoBoxCacheMax=1000 -Djava…high=300`, gives a cache reaching 1000. So the `-XX` flag wins in both directions, regardless of which value is larger. That rules out two independent paths with a max or a first-wins rule. Since `IntegerCache`'s source reads only `VM.getSavedProperty("java.lang.Integer.IntegerCache.high")` and nothing else, the only consistent explanation is that the VM writes that property into the startup map from the flag, overwriting whatever `-D` supplied. There is one configuration path with two front doors, and the flag is the outer one. The exact HotSpot call site that performs the write was not read, so the mechanism is inferred from the precedence measurement rather than quoted.

</details>

**Q3.** Why is `archivedCache` the only non-`final` field in `IntegerCache`, and why does that not weaken the class?

<details><summary>Answer</summary>

`CDS.initializeFromArchive` is a `native` method that writes the field from HotSpot's C++ side, outside any Java class initializer. The JVM rejects stores to a `final` static field from anywhere other than the declaring class's own `<clinit>`, so the field cannot be `final` if native code is to fill it. It does not weaken the class because `archivedCache` is not the field anything reads: the last line of the static block is `cache = archivedCache`, and `cache` is `static final Integer[]` annotated `@Stable`. `Integer.valueOf` reads only `IntegerCache.cache`, so the mutable field is a build-time staging slot that becomes unreachable-as-an-API the moment initialization ends. `@Stable` on `cache` additionally tells C2 it may treat the field and its elements as effectively constant after initialization, which it can do whether the array was mapped or constructed.

</details>

**Q4.** With `-XX:AutoBoxCacheMax=1000`, does the CDS archived subgraph get used? Justify from the log.

<details><summary>Answer</summary>

It gets mapped and then thrown away. Measured with `-Xlog:cds+heap=info`, the run still prints `resolve subgraph java.lang.Integer$IntegerCache`, `init subgraph java.lang.Integer$IntegerCache` and `initialize_from_archived_subgraph java.lang.Integer$IntegerCache 0x0000007000036b28 (early)` — so the native call found the subgraph and wrote `archivedCache`. Then the Java code evaluates `archivedCache == null || size > archivedCache.length`, where `size` = `(1000 - (-128)) + 1` = 1129 and `archivedCache.length` = 256. 1129 is greater than 256, so the `if` body runs, constructs 1,129 new `Integer` objects into a fresh array, and `archivedCache = c` overwrites the mapped reference. The process pays for both, and the mapped objects become immediately unreachable. That is the direct conflict between the tuning knob and the startup optimisation: raising the flag at all costs you the archive, and nothing warns you.

</details>

**Q5.** How many outcomes does `IntegerCache`'s static block have, and how many decision points produce them?

<details><summary>Answer</summary>

Two decision points, three outcomes. The first decision is inside `CDS.initializeFromArchive`, in native code: if a mapped CDS heap subgraph exists it writes `archivedCache`, otherwise it silently leaves it `null` — the javadoc's wording is that the fields *"remain as uninitialized if there is no mapped CDS java heap data"*. The second is the Java `if`: `archivedCache == null || size > archivedCache.length`. The outcomes are (a) subgraph present and large enough, so the loop never runs and `cache` points at the mapped array; (b) subgraph present but `size` exceeds its length, so it is discarded and the loop builds a new array; (c) no subgraph, short-circuit on the null test, loop builds the array. Note the call itself is unconditional — the class does not consult `CDS.isSharingEnabled()`, which exists in the same class; it calls and inspects.

</details>

**Q6.** `-Djava.lang.Integer.IntegerCache.high=banana` is templated into a deployment from an empty variable. What happens, and how does the `-XX` form differ?

<details><summary>Answer</summary>

Measured on JDK 21.0.7: the JVM starts normally with exit status 0, nothing is printed, and the cache is exactly the default — 127 interns, 128 does not. `Integer.parseInt("banana")` throws `NumberFormatException` inside the `try` block; the `catch` body is empty, with the JDK's comment `// If the property cannot be parsed into an int, ignore it.`; and `h` still holds its initializer value of 127 because `parseInt` is the first thing in the `try`. So a completely broken value is indistinguishable from an absent one. The `-XX` form behaves oppositely: `-XX:AutoBoxCacheMax=banana` is validated by HotSpot's option parser before any Java runs and refuses to boot, printing `Improperly specified VM option 'AutoBoxCacheMax=banana'` and `Error: Could not create the Java Virtual Machine.` If you must set this value, use the flag form so the failure is loud, and assert the resulting `==` behaviour on startup anyway.

</details>

**Q7.** Someone says "the `Integer` cache is built by a loop that allocates 256 objects when `Integer` is first touched". What is wrong with that on Java 21?

<details><summary>Answer</summary>

It describes the uncommon path. The default CDS archive ships inside the JDK image and `-Xshare:auto` is the default sharing mode, so on a default Java 21 start `CDS.initializeFromArchive` finds a mapped heap subgraph, `archivedCache` is non-`null` with length 256, `size` is also 256, and the loop is dead code. Measured: `java -Xlog:cds+heap=info -version` prints `initialize_from_archived_subgraph java.lang.Integer$IntegerCache` on a default start and **zero** `cds,heap` lines under `-Xshare:off`. The loop runs only under `-Xshare:off`, on an image with a missing or mismatched archive, or when the tuning flag pushed `size` past 256. The statement was true before archived heap subgraphs existed — JDK 8's `Integer.java` has no `archivedCache` field at all — so it is a version-stale answer rather than a wrong one, and the right move in an interview is to give the 21 mechanism and name the older one.

</details>

**Q8.** Can you tell an archived `Integer` from a constructed one at runtime?

<details><summary>Answer</summary>

Not through any documented means, and the measurements do not support the obvious guess. `Integer.valueOf` reads `IntegerCache.cache[i + (-IntegerCache.low)]` and the last line of the static block is `cache = archivedCache`, so the field points at either array indistinguishably — that indistinguishability is the design goal. `System.identityHashCode(Integer.valueOf(0))` does differ between configurations, measured as 692404036 under `-Xshare:auto` and 1450821318 under `-Xshare:off`, reproducibly across runs. But it is not evidence of an archive marker: the addresses in the `cds,heap` log show the mapping base changing between runs (`0x000000c8…` versus `0x00000070…`) while the identity hash does not change, so the hash is not address-derived; and with `-XX:AutoBoxCacheMax=1000`, where the object is definitely freshly constructed, the hash is still 692404036. That points at HotSpot's identity-hash generator simply being deterministic per configuration rather than at anything about the object. The only reliable observation is external: `-Xlog:cds+heap=info` and look for `initialize_from_archived_subgraph`.

</details>

## Open questions

- **Where HotSpot translates `-XX:AutoBoxCacheMax` into the saved property.** Established by measurement: there is one configuration path, and the flag overrides a conflicting `-D` in both directions, which given that `IntegerCache` reads only the property means the VM must write the property from the flag. Not established: the C++ call site. What would settle it — `grep -rn AutoBoxCacheMax` over `hotspot/share` in an OpenJDK 21 source tree, expecting hits in `opto/c2_globals.hpp` for the declaration and in `runtime/arguments.cpp` for the property write.
- **Whether C2 consumes `AutoBoxCacheMax`'s value.** Established: the flag is categorised `{C2 product}`, meaning it is declared in C2's flag table, and a separate flag `EliminateAutoBox = true {C2 product} {default}` exists and is unambiguously the box-elimination switch. Not established: whether C2's own box-identity reasoning reads `AutoBoxCacheMax`. What would settle it — the same `grep` over `hotspot/share/opto`; a hit only in `c2_globals.hpp` would mean the flag is C2-declared but not C2-consumed.
- **The meaning of the `(early)` marker** on `initialize_from_archived_subgraph java.lang.Integer$IntegerCache`, present on `Integer$IntegerCache` and absent on `Long$LongCache` in every measured run. `jdk/internal/misc/CDS.java` on JDK 21.0.7 has exactly one form of `initializeFromArchive` with no early/late parameter, so the distinction is entirely HotSpot-side and cannot be settled from Java source. What would settle it — reading the log site in `hotspot/share/cds/heapShared.cpp`, where the subgraph registration presumably carries an "is early" attribute distinguishing subgraphs initialised before the full module graph from those initialised after.
- **Why `System.identityHashCode(Integer.valueOf(0))` is reproducibly 692404036 on the archived path and 1450821318 under `-Xshare:off`.** Established: the values are stable across runs within a configuration; they are not address-derived, since the mapped base changes between runs while the hash does not; and the value on the archived path is unchanged when `-XX:AutoBoxCacheMax=1000` forces the object to be freshly constructed. Not established: whether the archive carries a pre-computed hash in the archived mark word, or whether HotSpot's identity-hash PRNG is deterministic and consumes a different number of values before `main` on the two paths — the third measurement favours the second explanation. What would settle it — reading `ObjectSynchronizer::FastHashCode` and `get_next_hash` in `hotspot/share/runtime/synchronizer.cpp` together with the archived-object mark-word handling in `heapShared.cpp`.

---

**Leaves covered:** 3.4.3, 3.4.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 750
