# 03 Java Core — Serialization: the attack surface, filters and the practical rule — INTERMEDIATE (§2.10, 2.10.10–2.10.12)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Externalizable, records and lambdas](02b-externalizable-records-and-lambdas.md) · Next: [Null discipline](../null-discipline/02-null-discipline.md)

`02-serialization.md` owns the marker interface, the object graph, `serialVersionUID`, `transient`
and compatibility. `02a` owns the five hooks, the constructor bypass, and the serialization proxy.
`02b` owns `Externalizable`, records, and lambda serialization. This file closes §2.10 with the
security case, the JEP 290 filter API, and the practical rule for when to use any of this at all.
The question this file answers, in bold: **why is `ObjectInputStream.readObject()` on bytes you
did not write a remote-code-execution primitive, and what do you actually do about it?**

## 1. Deserialization of untrusted data as an RCE class (2.10.10)

A JSON parser reads bytes into a tree and hands the tree to you. `ObjectInputStream.readObject()`
reads bytes that **name classes**, loads those classes, allocates instances of them, and **runs
their code** — their `readObject`, their `readResolve`, their `validateObject` — before your first
line of application logic sees anything at all. **`readObject()` is not a parser, it is an
interpreter.** The byte stream is a small program; the JVM is its runtime, and it starts executing
before your cast, your `instanceof`, or your validation ever runs.

### Why it exists

The vulnerability is not a bug bolted onto serialization; it is the direct, documented consequence
of the design covered across `02`, `02a`, and `02b`. Serialization was built to reconstruct
arbitrary object graphs, including private state, without going through a constructor, because
that is what transparent persistence and RMI needed in 1997. Nobody designing that mechanism was
asking "what if the byte stream is adversarial" — the threat model was a trusted peer JVM talking
RMI. Thirty years later the same API is reachable from HTTP request bodies, message queue
payloads, and cache values, and the trust assumption never got restated.

### How it works

The mechanism, step by step, each one grounded in something already established in this file set:

1. The stream carries a class **name** as text, not a class reference. On the measured JDK 21.0.7
   build used throughout this file set, editing a class name inside a captured byte stream and
   replaying it produced `java.lang.ClassNotFoundException: Ver3XNoUid` — proof that the name is
   attacker-controlled data, and that it is resolved and loaded **before** any `serialVersionUID`
   check or type check happens.
2. Resolving that name loads the class, so static initialization can run — see
   `../classes-and-initialization/01d-class-initialization-triggers.md` for the trigger list.
3. An instance is allocated **without its constructor running** — the bypass mechanism `02a` walks
   in full — and fields are injected directly from the stream.
4. Any `readObject`, `readResolve`, or `validateObject` present on any class in the graph then
   runs, per the hook lookup `02a` describes.
5. Steps 1–4 happen for **every class reachable in the graph**, including classes the caller never
   intended to receive. The type the caller casts the result to is checked **last**, by the
   ordinary Java cast, after the stream has already finished executing.

**Insight:** `(LedgerEntry) ois.readObject()` reads like a type guarantee — as if the stream could
only have produced a `LedgerEntry` or thrown before doing anything else. It cannot. `readObject()`
returns `Object`; the JVM has already loaded classes, bypassed constructors, and run every hook
method in the graph by the time your cast executes. The cast rejects the *result*; it does nothing
to the *side effects* that produced it. Believing the expected type constrains the stream is the
single most common wrong mental model of this API.

A gadget chain is what an attacker builds on top of step 5: a graph composed entirely of classes
**already present on your classpath** — never classes the attacker supplies — chosen so that the
`readObject` (or `readResolve`, or a getter invoked from a `toString`, or a comparator invoked from
a sorted-collection's own deserialization) of one class reaches a method on the next, and the
composition eventually reaches a dangerous sink: a reflective invocation, a template engine, a
script engine, a process launcher, a JNDI lookup. No single class in the chain has a bug — each is
doing exactly what its own Javadoc says. The vulnerability lives in the *composition*, which is why
patching one library never closes it, and why every dependency you add to the classpath widens the
reachable graph whether or not you ever call that dependency's API directly. `ysoserial` is the
well-known public research tool that catalogues known chains found in common libraries (Apache
Commons Collections, Spring, Groovy, and others across its history); it is as much a defender's
inventory of what to check for as it is an attacker's toolkit, and running it against your own
classpath is a legitimate way to find out what you are exposed to. Guide 13 (Web security) gives
the full gadget-chain treatment, walkthroughs of specific published chains, and how they were
found — this file gives you enough of the mechanism to answer the interview question and to reason
about the shape of the risk; go there for the exploit-level detail. **This file deliberately does
not enumerate a chain or name a class sequence — see the scope note governing this document.**

Why this class of bug is uniquely bad in Java, as a short list with the reason for each:

| Reason | Why it matters |
|---|---|
| Surface is your transitive dependency graph, not your code | Every library on the classpath is a potential gadget link whether or not you call it |
| No allow-list by default | Measured on this JDK: `ObjectInputFilter.Config.getSerialFilter()` returns `null` out of the box — nothing is rejected unless you configure it |
| Entry points are unobvious | `ObjectInputStream` hides inside RMI, JMX, some HTTP session stores, some caches, some message-queue clients, some JDBC drivers |
| Cannot be fixed class-by-class | The bug is compositional; patching one class in a chain does not remove the other links still on the classpath |

Frame the exposure in QuizStakes concretely, because "somewhere on the internet" is not how these
get found — they get found at a specific boundary that someone forgot was a boundary:

- an HTTP session store that serializes a session object holding a `Reservation`, if that store's
  deserialization path is reachable from outside the trust boundary;
- a cache or message payload carrying a `LedgerEntry` or `PaymentIntent` between services over
  `RouterInt`, if the transport uses Java serialization instead of a document format;
- a JMX or RMI management endpoint exposed on `InternalPlatforms`, since both protocols use Java
  serialization as their wire format by default;
- an operator-facing `PaymentRun` import that accepts an uploaded file, if that file is ever passed
  to `ObjectInputStream` rather than parsed as data.

The blast radius is worth stating in the domain's own numbers. `FundsLedger` is the sole source of
truth for money, writing roughly 19.8M entries per day with 7 years of retention — about 1.3 TB per
year of the fact record for every stake, deposit, and withdrawal. Code execution inside the process
that writes that ledger is not a data breach; it is the ability to create money. The invariant an
attacker wants to break is exactly the one `StakeSplit` exists to protect: a 3.33 stake must split
as 0.33 bonus + 3.00 cash, never 0.34 + 3.00 = 3.34, because the second form manufactures a minor
unit of money on every stake at scale. A gadget chain that reaches arbitrary code inside the
ledger-writing process can write an entry that violates that invariant directly, with no forged
signature and no compromised credential required — just a byte stream the process was willing to
deserialize.

Version note: nothing about the vulnerability class changed between Java 8 and 21 — the mechanism
in steps 1–5 above is unchanged specification behavior. What changed is the tooling around it:
filters arrived in 9 (JEP 290), the filter factory arrived in 17 (JEP 415), covered next.

**Interview:** "Why is Java deserialization dangerous?" The one-line answer: because
`readObject()` runs code (constructors bypassed, hooks executed, classes loaded) for every class
named in the stream before your application ever inspects the result, so an attacker who controls
the bytes controls what code runs, using only classes already on your classpath.

> Deserializing untrusted bytes with `ObjectInputStream` executes attacker-chosen code paths made
> of classes already on the classpath, because class resolution, allocation, and hook execution all
> happen before the caller's type check does.

## 2. JEP 290 serialization filters (2.10.11)

Picture a filter as a **checkpoint wired between the stream and `Class.forName`**. Every class the
stream names, and every array length, graph depth, reference count, and byte total the stream
reports, is offered to the filter before the JVM acts on it, and the filter answers one of three
things: allow it, reject it, or defer.

### Why it exists

JEP 290 (targeted for JDK 9, and backported to earlier update releases) exists because removing
`ObjectInputStream` outright was never viable — too much of the platform and too many applications
depend on it — so the fix chosen was to let an application declare, before any untrusted byte
reaches the stream, exactly which classes it is willing to materialize. That is an allow-list
placed at the one point in the pipeline that sees every class name before it is resolved.

### How it works

`java.io.ObjectInputFilter` is a functional interface with one method: `Status checkInput(FilterInfo
filterInfo)`. `Status` is the enum `ALLOWED`, `REJECTED`, `UNDECIDED`. `FilterInfo` exposes five
accessors: `serialClass()` (the class being checked; `null` for checks that are not about a
specific class, such as an array-length or depth check — a real trap if a hand-written filter calls
a method on it without a null check), `arrayLength()` (length being allocated, or `-1` if not
applicable), `depth()` (current graph depth), `references()` (count of object references seen so
far in the stream), and `streamBytes()` (bytes consumed so far).

**Pitfall:** `UNDECIDED` is not "allow." It means "defer to whatever decides next," and if nothing
in the chain ever returns `ALLOWED` or `REJECTED`, the default is to allow. This is exactly why
every hand-written pattern filter must end with a catch-all `!*` — a filter that only lists allowed
classes and never rejects the rest allows everything it did not think to name.

The pattern grammar, via `ObjectInputFilter.Config.createFilter(String)`: entries are
semicolon-separated; a leading `!` on a class-name entry rejects instead of allows; `*` matches one
package level and `**` matches recursively, so `com.quizstakes.*` matches classes directly in that
package and `com.quizstakes.**` matches that package and every subpackage; `maxdepth=`,
`maxarray=`, `maxrefs=`, and `maxbytes=` set limits that reject once exceeded rather than naming a
class at all.

Three patterns were measured against the harness class below on Oracle JDK 21.0.7
(build 21.0.7+8-LTS-245), macOS aarch64:

```java
static class Trans implements Serializable {
    private static final long serialVersionUID = 1L;
    int stakeMinor = 420;
    transient String pspToken = "tok-secret";
    static int shared = 99;
}
```

deserialized through:

```java
try (var ois = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
    ois.setObjectInputFilter(ObjectInputFilter.Config.createFilter(pattern));
    return ois.readObject();
}
```

| Pattern | Measured result |
|---|---|
| `!*` | `java.io.InvalidClassException: filter status: REJECTED` |
| `Ver5$Trans;!*` | Succeeded — returned `Trans[stakeMinor=420, pspToken=null, shared=99]` |
| `maxdepth=1;maxbytes=10` | `java.io.InvalidClassException: filter status: REJECTED` |

The exception message is identical (`filter status: REJECTED`) whether a class was refused by name
or a limit was exceeded — the message alone does not tell you *why*. That matters operationally: if
you cannot tell a legitimate schema addition (needs an allow-list update) from an attack (needs no
change and an alert) from the exception text, you must log the filter's own decision, not just the
resulting exception. Guide 20 (Observability) owns where that logging belongs in a service.

Filters exist at three scopes:

| Scope | How it is set | When it applies | Runtime-changeable | What it is for |
|---|---|---|---|---|
| Per-stream | `ObjectInputStream.setObjectInputFilter(filter)` | That one stream instance only | No — set once per stream, before the first `readObject()` | A single call site with a known, narrow shape of expected classes |
| Process-wide | `-Djdk.serialFilter=<pattern>`, or the `jdk.serialFilter` property in `conf/security/java.properties` | Every `ObjectInputStream` in the JVM that does not otherwise reject it | No — read once at JVM/property load | A blanket floor across a whole process, e.g. a container platform default |
| Filter factory (JEP 415, JDK 17+) | `-Djdk.serialFilterFactory=<class>` or `ObjectInputFilter.Config.setSerialFilterFactory(factory)` | Invoked on **every** `ObjectInputStream` construction, given the current process filter and the stream's own requested filter | Settable once per process (throws if already set and not still the built-in default) | Lets a container compose a context-specific filter with the process filter instead of one silently overriding the other |

Measured on the same JDK 21 run, with no filter-related flags set: `ObjectInputFilter.Config
.getSerialFilter()` returned **`null`** — there is no process-wide filter by default on JDK 21.
That is the most important fact in this section: an unconfigured JDK 21 process rejects nothing.
Also measured: `ObjectInputFilter.Config.getSerialFilterFactory()` returned
`java.io.ObjectInputFilter$Config$BuiltinFilterFactory` — a factory is always installed, even when
no custom filtering is configured, and JEP 415 is precisely what lets you replace that built-in
factory with your own.

What JEP 415 changed: before JDK 17, a per-stream filter and a process-wide filter did not compose
— a stream filter, where the platform allowed setting one at all, effectively replaced rather than
combined with the process filter, so a library that wanted to enforce its own filter could stomp on
or be stomped by whatever the embedding application had configured. The filter factory is invoked
for every `ObjectInputStream` at construction time and is handed both the current static filter and
the stream's requested filter, so it can combine them explicitly. `ObjectInputFilter` itself
declares four `static` composition helpers, added by JEP 415 alongside the filter factory and
present on JDK 21 — confirmed by reading `java.base/java/io/ObjectInputFilter.java` in
`lib/src.zip` of Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245):

```java
static ObjectInputFilter allowFilter(Predicate<Class<?>> predicate, Status otherStatus);
static ObjectInputFilter rejectFilter(Predicate<Class<?>> predicate, Status otherStatus);
static ObjectInputFilter merge(ObjectInputFilter filter, ObjectInputFilter anotherFilter);
static ObjectInputFilter rejectUndecidedClass(ObjectInputFilter filter);
```

`allowFilter` and `rejectFilter` turn a class predicate into a filter that returns the given
`Status` (or `UNDECIDED`, per the predicate's negation) for a class check; `merge` composes two
filters so that a `REJECTED` from either wins; `rejectUndecidedClass` wraps a filter so that any
class-name check it would otherwise leave `UNDECIDED` becomes `REJECTED`, without touching the
non-class checks (`serialClass() == null`) that a factory still wants to defer. The exact name is
`rejectUndecidedClass`, not the shorter `rejectUndecided` sometimes seen in informal write-ups.

Complete, compiling code: a filter for a `PaymentRun` import that allows exactly the value types
such an import may legitimately carry, rejects everything else, and logs its own decision so the
message-text ambiguity above does not bite in production.

```java
final class PaymentRunImportFilter implements ObjectInputFilter {

    private static final Set<String> ALLOWED = Set.of(
            "com.quizstakes.payments.PaymentRun",
            "com.quizstakes.payments.WithdrawalTransaction",
            "com.quizstakes.money.Money",
            "java.math.BigDecimal",
            "java.util.Currency",
            "java.util.ArrayList",
            "java.util.UUID");

    @Override
    public Status checkInput(FilterInfo filterInfo) {
        if (filterInfo.references() > 5_000 || filterInfo.depth() > 20
                || filterInfo.streamBytes() > 1_000_000L) {
            log(filterInfo, Status.REJECTED, "limit exceeded");
            return Status.REJECTED;
        }
        Class<?> clazz = filterInfo.serialClass();
        if (clazz == null) {
            return Status.UNDECIDED;
        }
        Status status = ALLOWED.contains(clazz.getName()) ? Status.ALLOWED : Status.REJECTED;
        log(filterInfo, status, clazz.getName());
        return status;
    }

    private void log(FilterInfo info, Status status, String detail) {
        System.getLogger(PaymentRunImportFilter.class.getName())
                .log(System.Logger.Level.INFO,
                        "serialFilter status={0} class={1} depth={2} refs={3}",
                        status, detail, info.depth(), info.references());
    }
}
```

The equivalent as a pattern string, with the mandatory terminator:

```java
String pattern = "com.quizstakes.payments.PaymentRun;"
        + "com.quizstakes.payments.WithdrawalTransaction;"
        + "com.quizstakes.money.Money;"
        + "java.math.BigDecimal;java.util.Currency;java.util.ArrayList;java.util.UUID;"
        + "maxdepth=20;maxrefs=5000;maxbytes=1000000;!*";
```

Wired into the read path an operator-facing import would use:

```java
static PaymentRun readPaymentRunImport(byte[] bytes) throws IOException, ClassNotFoundException {
    try (var ois = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
        ois.setObjectInputFilter(new PaymentRunImportFilter());
        return (PaymentRun) ois.readObject();
    }
}
```

The `!*` at the end of the pattern form, or the `Status.REJECTED` default in the hand-written form,
is what makes this an allow-list rather than a suggestion. Omitting it is the second-most common
filter bug after not installing a filter at all — a filter with entries but no terminator allows
everything it forgot to reject, per the `UNDECIDED`-defers-to-allow rule above.

### Pitfall — filters only cover `ObjectInputStream`

**Pitfall:** setting `jdk.serialFilter` protects `ObjectInputStream.readObject()` and nothing else.
It does nothing for Jackson, SnakeYAML, Kryo, XStream, or any other library that builds objects
from a document, because none of those libraries call `ObjectInputStream.readObject()` — they walk
their own document format and construct objects with their own reflection or codegen. A team that
sets `jdk.serialFilter`, watches it reject a crafted payload in a test, and closes the ticket has
usually hardened a surface they were not using in the first place and left the one that a modern
Spring Boot service actually exposes: a JSON body deserialized by Jackson with polymorphic type
handling enabled, or a YAML document parsed by SnakeYAML's default loader.

The shape of the parallel is worth being precise about, because the defence transfers but the API
does not: a JSON document carrying a type discriminator field that a library resolves to a concrete
class and instantiates is the *same* vulnerability — attacker-controlled data naming a class that
gets loaded and constructed — with different bytes. The mitigation is the same shape, an allow-list
of permitted concrete types, but it is configured through each library's own mechanism (Jackson's
`PolymorphicTypeValidator`, for instance), not through `jdk.serialFilter`. Guide 13 (Web security)
owns the full treatment of those library-specific mitigations; guide 07 (Spring core) owns where a
Spring Boot 3.x application ends up with one of these paths enabled without anyone deliberately
choosing it, for example a session store or a message converter configured for polymorphic
deserialization by default.

The honest limits of filters even on the surface they do cover: a filter constrains *which* classes
are materialized, not what an allowed class's own `readObject` then does once materialized; a
filter cannot inspect field *values*, only class identity and stream shape; an allow-list has to be
maintained as the schema evolves, and a stale one fails closed in production the next time a
legitimate new field type ships; and the `maxbytes`/`maxdepth`/`maxrefs` limits are the only defence
this API offers against a resource-exhaustion stream — a payload naming only allowed classes can
still be built to consume excessive memory or stack depth, so leaving the limits unset means a
small, fully-allowed payload can still cost you the JVM.

**Interview:** "If I set `jdk.serialFilter`, am I protected against deserialization attacks in my
Spring Boot service?" The one-line answer: only for the paths that actually call
`ObjectInputStream.readObject()` — session stores, RMI, JMX, and any custom Java-serialization
transport; a filter does nothing for Jackson, SnakeYAML, or Kryo, which need their own
library-specific allow-listing.

> A `jdk.serialFilter` (or per-stream `ObjectInputFilter`) is an allow-list checkpoint that
> `ObjectInputStream` consults before resolving a class named in the stream, and it covers only
> code paths that call `ObjectInputStream.readObject()` — nothing else.

## 3. The practical rule: do not use Java serialization for persistence or wire formats (2.10.12)

Every problem `02`, `02a`, `02b`, and this file walk through is downstream of one decision: using a
serialization mechanism that **names classes in the byte stream** as if it were a **data format**.
A data format should describe data — a discriminated bag of values. Java's serial form describes
*objects*, which under the hood means it describes *code to run to reconstruct them*, which is why
reading it means running code.

### Why it exists

The rule is not "serialization is broken and should never be touched" — `02a` and `02b` show it
correctly used for its native purpose, transparent object-graph transfer between trusted JVMs. The
rule is narrower and sharper: **do not choose it as your persistence format or your service-to-
service wire format**, because both of those roles routinely put the byte stream in a position
where it crosses a trust boundary or outlives the code that wrote it, and Java's serial form is
uniquely bad at both.

### How it works

The choice among formats is decided on a small number of axes, and Java serialization loses on
nearly all of them for this use case:

| Axis | Java serialization | JSON (Jackson) | Protobuf | Avro |
|---|---|---|---|---|
| Schema is explicit | No — implicit in bytecode, inferred via reflection | No, unless a JSON Schema is maintained separately | Yes — `.proto` file, versioned | Yes — `.avsc` schema, versioned |
| Cross-language | No — JVM-only wire format | Yes | Yes | Yes |
| Forward/backward field evolution | Fragile — governed by `serialVersionUID` and default-value rules `02` covers, no removal story | Tolerant by convention, but only as strict as hand-written deserialization code makes it | Strong — field numbers, defined default/removal rules | Strong — schema resolution rules defined by the format |
| Size on the wire | Large — carries full class descriptors per stream | Verbose — field names repeated per record | Compact — binary, field numbers not names | Compact — binary, schema carried separately from data |
| Reading it can execute code | Yes — always, per Concept 1 of this file | Yes, if polymorphic type handling is enabled; no otherwise | No | No |
| Tooling for schema review | None — the "schema" is a compiled class file | Ad hoc unless a schema is bolted on | Yes — `.proto` diffed in code review | Yes — `.avsc` diffed in code review |

The JSON row is deliberately not a clean win: with polymorphic type handling switched off, plain
JSON deserialization into a fixed target type does not execute arbitrary code, which is why it is
the right choice for many boundaries — but the moment a service turns on a discriminator-driven
polymorphic mapping to support a class hierarchy over the wire, it reintroduces exactly the
code-execution column that made Java serialization unacceptable, per the parallel drawn in Concept
2's pitfall. The honest comparison keeps that nuance rather than presenting JSON as an
unconditional replacement.

For QuizStakes specifically: a `LedgerEntry` retained for 7 years needs an explicit, reviewable,
versioned schema, so Avro or Protobuf, not Java serialization and not schema-less JSON — at roughly
19.8M ledger entries written per day against 7-year retention, a reader running today will
routinely open rows written by a build of the service that no longer exists anywhere, so
field-name-based, defaulted, schema-checked evolution is not a nicety, it is the only way those
rows stay readable at all. A `RouterInt` request or response between services needs a contract that
another team's codebase can read without depending on your class files, so JSON with an explicit,
reviewed schema and no polymorphic type handling, or Protobuf where the throughput justifies binary
tooling. Nothing in the platform needs Java serialization on a wire or in a durable store. Guide 12
(API design) owns the full wire-format decision for service contracts; guide 14 (System design)
owns the durable-storage-format decision at the ledger's scale and retention profile.

Because "stop using it" is not actionable against a running system, the migration is a playbook,
not a single change, and the steps are not equally reversible:

1. **Inventory every entry point.** Grep the codebase and its configuration for
   `ObjectInputStream`, `readObject`, `Externalizable`, `implements Serializable`, and the
   framework settings that enable session serialization or expose RMI/JMX. This step is fully
   reversible — it changes nothing.
2. **Close the externally-reachable entry points first.** Anything a request from outside the trust
   boundary can drive — an HTTP session store, an operator upload, a queue consumer fed by another
   team — is the priority, ranked above internal, fully-trusted JVM-to-JVM RMI links.
3. **Put a `!*`-terminated filter and byte/depth/reference limits on anything that must stay Java
   serialization in the meantime.** Reversible, and buys time, but per Concept 2's limits section it
   is a mitigation, not a fix — it does not remove the code-execution surface from an allowed class.
4. **Convert persisted or transported forms to a schema format behind a version-tagged reader that
   can read both the old and the new form during the cutover.** This is where the work actually is;
   still reversible in principle by keeping the dual-read path, but increasingly costly to reverse
   the longer both forms are live.
5. **Remove `Serializable` from the domain types once nothing reads the old form.** This step is
   **not reversible** without regenerating historical data in the old format — treat it as the point
   of no return and do it last, after retention-window data has either been migrated or aged out.

Finally, the direction of travel, stated as intent rather than a schedule. Java serialization is a
recognized long-term liability inside OpenJDK itself: JEP 290's own motivation and the JDK's
continued "Serialization Filtering" investment (extended by JEP 415) are explicit acknowledgments
that the mechanism needs an external safety net it was never designed with, and records' canonical-
constructor deserialization path — covered in `02b` — is the shape of a replacement already
shipped: reconstruction that goes through a constructor and validates, rather than one that bypasses
it. **There is no announced removal release for `Serializable` or `ObjectInputStream`, and this
file does not claim one exists** — do not repeat "Java serialization is being removed" as a fact in
an interview; the accurate claim is narrower: the platform is investing in constructor-respecting
alternatives and in filtering the legacy path, not in deleting it on a schedule. **Unverified:** no
specific JEP number is cited here for a future full replacement of `ObjectInputStream`'s default
protocol, because none is confirmed; if one is needed, verify it against the OpenJDK JEP index
before citing a number.

**Interview:** "Should we ever use Java's built-in serialization in a new service?" The one-line
answer: no — use it only for its narrow native case of transferring trusted object graphs between
JVMs you control (RMI internals, certain caching layers under your own trust boundary), never for
persistence or for any wire format that crosses a service or a trust boundary; use Avro or Protobuf
for durable schemas and JSON or Protobuf for service contracts.

> Java's built-in serialization ties your data format to your bytecode and your bytecode's ability
> to run code on deserialization, which is why persistence and wire-format roles belong to an
> explicit, cross-language, non-executable schema format instead — JSON, Protobuf, or Avro.

## Pitfalls

### Believing a `jdk.serialFilter` protects the whole application against deserialization attacks

**Wrong**

```java
// Launch flag: -Djdk.serialFilter=com.quizstakes.**;!*
// Team closes the security ticket: "deserialization hardened, filter installed."
// Meanwhile the same service accepts a JSON body here:
ObjectMapper mapper = new ObjectMapper();
mapper.activateDefaultTyping(mapper.getPolymorphicTypeValidator());
PaymentIntent intent = mapper.readValue(requestBody, PaymentIntent.class);
// The jdk.serialFilter flag never sees this call. Jackson never touches
// ObjectInputStream. A crafted requestBody naming a gadget-reachable type
// is resolved and instantiated with no filter in the path at all.
```

**Right**

```java
ObjectMapper mapper = JsonMapper.builder()
        .polymorphicTypeValidator(BasicPolymorphicTypeValidator.builder()
                .allowIfSubType("com.quizstakes.payments.")
                .allowIfSubType("com.quizstakes.money.")
                .build())
        .build();
// No default typing enabled at all is stronger still: bind to a concrete,
// non-polymorphic target type wherever the schema allows it.
PaymentIntent intent = mapper.readValue(requestBody, PaymentIntent.class);
```

**Why people believe it:** the `jdk.serialFilter` flag is process-wide, so it reads like a blanket
guarantee, and the security scanner that flagged "unrestricted deserialization" in the first place
was almost certainly pattern-matching on `ObjectInputStream`, so fixing that one finding felt like
closing the whole class of bug.

### Believing the cast after `readObject()` constrains what the stream can build

**Wrong**

```java
Object raw = ois.readObject();
LedgerEntry entry = (LedgerEntry) raw;   // "this will throw ClassCastException
                                          // if the stream isn't a LedgerEntry,
                                          // so I'm safe before this line"
```

**Right**

```java
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
        "com.quizstakes.ledger.LedgerEntry;java.math.BigDecimal;"
        + "java.util.Currency;java.time.Instant;!*");
try (var ois = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
    ois.setObjectInputFilter(filter);
    LedgerEntry entry = (LedgerEntry) ois.readObject();
}
```

**Why people believe it:** in almost every other Java API, a cast is the last line of defence
against the wrong type reaching your code, and it throws before you can act on bad data — so it
feels natural to assume the same ordering here, when in fact `readObject()` has already loaded
classes, bypassed constructors, and executed every hook in the graph by the time the cast token is
even reached.

### Believing filters replace removing `Serializable` rather than buying time to do it

**Wrong**

```java
// "We added a filter, so the payment domain types can stay Serializable
// and go over the message queue as-is." — ticket closed, no further work.
class PaymentIntent implements Serializable { /* fields as before */ }
```

**Right**

```java
// Filter installed as an interim control on the existing consumer, while the
// producer and consumer are migrated in parallel to a schema format, after
// which PaymentIntent drops "implements Serializable" entirely:
try (var ois = new ObjectInputStream(queueBytes)) {
    ois.setObjectInputFilter(paymentDomainFilter);
    PaymentIntent legacy = (PaymentIntent) ois.readObject();
}
record PaymentIntentV2(ClientId clientId, Money amount, Instant requestedAt) {}
```

**Why people believe it:** a filter that visibly rejects a crafted payload in a test looks like the
problem is solved, and removing `Serializable` from a domain type touched by several services feels
like a large, risky change compared to adding one JVM flag — so the smaller, reversible fix gets
mistaken for the complete one.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Core danger | `readObject()` loads classes, bypasses constructors, and runs hooks before your type check runs |
| Class name in stream | Attacker-controlled text, resolved before any `serialVersionUID` check (measured: `ClassNotFoundException` on edited name) |
| Gadget chain | Composition of classes already on the classpath; no single class is buggy |
| `ysoserial` | Public research tool cataloguing known chains; useful for defenders auditing their own classpath |
| Default process filter (JDK 21) | `getSerialFilter()` returns `null` — nothing rejected unless configured |
| Default filter factory (JDK 21) | `ObjectInputFilter$Config$BuiltinFilterFactory`, always installed |
| `ObjectInputFilter.checkInput` | Returns `ALLOWED`, `REJECTED`, or `UNDECIDED` per `FilterInfo` |
| `UNDECIDED` meaning | Defers to next filter/default; default with nothing deciding is allow |
| Pattern terminator | End every pattern filter with `!*`, or default to reject in a hand-written one |
| `serialClass()` on non-class checks | `null` — check before dereferencing |
| Scopes | Per-stream, process-wide (`jdk.serialFilter`), filter factory (`jdk.serialFilterFactory`, JDK 17+, JEP 415) |
| JEP 415's contribution | Lets a factory compose the process filter with a per-stream/context filter instead of one silently winning |
| Filter blind spot | Covers only `ObjectInputStream`; Jackson/SnakeYAML/Kryo need their own allow-listing |
| Filter cannot check | Field values, or what an allowed class's own code does once allowed |
| The rule | No Java serialization for persistence or wire formats — use JSON/Protobuf/Avro |
| JSON caveat | Polymorphic type handling reintroduces code-execution risk |
| Irreversible migration step | Removing `Serializable` from the domain type, once nothing reads the old form |

## Self-test

**Q1.** Why is casting the result of `readObject()` not a safety boundary against a malicious byte stream?

<details><summary>Answer</summary>

Because the cast is checked last. By the time `(LedgerEntry) ois.readObject()` evaluates its cast,
the JVM has already resolved every class named anywhere in the graph, allocated instances of them
without running their constructors, and executed any `readObject`, `readResolve`, or
`validateObject` hooks present on any of those classes. The cast only rejects the final returned
reference if its runtime type is wrong; it has no ability to prevent or undo the code that already
ran while the graph was being reconstructed.

</details>

**Q2.** What does `ObjectInputFilter.Config.getSerialFilter()` return on an unconfigured JDK 21 process, and why does that matter?

<details><summary>Answer</summary>

It returns `null`, as measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245, macOS aarch64). It
matters because it means there is no process-wide allow-list by default: an application that never
explicitly configures `jdk.serialFilter`, a filter factory, or a per-stream filter will resolve and
instantiate any class named in a stream handed to `ObjectInputStream.readObject()`, with nothing in
the platform rejecting it automatically.

</details>

**Q3.** What is a gadget chain, at the mechanism level, and why can't patching one library class fix it?

<details><summary>Answer</summary>

A gadget chain is a graph of classes that are already present on the target's classpath, selected
by an attacker so that the deserialization-time behavior of one class (its `readObject`,
`readResolve`, or a method invoked incidentally during reconstruction) invokes a method on the
next, and the chain of invocations eventually reaches a dangerous sink such as reflective
invocation or a script engine. No individual class in the chain is misbehaving relative to its own
contract; the vulnerability is the composition. Patching or removing one class only breaks that
particular chain — any other combination of classes still on the classpath that reaches the same
class of sink remains exploitable, which is why the defence has to be at the entry point (a filter,
or removing the entry point entirely) rather than at any single class in a chain.

</details>

**Q4.** A service sets `-Djdk.serialFilter=com.quizstakes.**;!*` and also accepts JSON with Jackson default typing enabled on an internal endpoint. Is the service protected against deserialization attacks?

<details><summary>Answer</summary>

No, not against the Jackson path. `jdk.serialFilter` only intercepts calls into
`ObjectInputStream.readObject()`; Jackson does not call that method, so the filter has no effect on
what Jackson will instantiate. With default typing enabled, Jackson resolves a type discriminator
embedded in the JSON document to a concrete class and instantiates it — the same category of
vulnerability (attacker-controlled data naming a class that gets loaded and constructed) reached
through a completely different API that the `jdk.serialFilter` flag does not touch. The Jackson
path needs its own mitigation, such as a `PolymorphicTypeValidator` allow-list or disabling default
typing outright.

</details>

**Q5.** What is the difference between what `UNDECIDED` and `REJECTED` mean when returned from `ObjectInputFilter.checkInput`, and why does a pattern filter need a trailing `!*`?

<details><summary>Answer</summary>

`REJECTED` immediately fails the deserialization with an `InvalidClassException`. `UNDECIDED` makes
no decision at all — it defers to whatever the next filter in a composed chain decides, and if
nothing in the chain ever decides, the outcome is to allow. A pattern filter that lists only allowed
class names and stops there returns `UNDECIDED` for anything not matched, which resolves to allow;
appending `!*` makes every unmatched class explicitly `REJECTED` instead, turning the filter from a
partial allow-list that silently permits the rest into a true allow-list.

</details>

**Q6.** Name two attributes on `ObjectInputFilter.FilterInfo` that are not about the class being deserialized, and what they defend against.

<details><summary>Answer</summary>

`maxdepth`-checked `depth()` and `maxbytes`-checked `streamBytes()` (also `arrayLength()` against
`maxarray` and `references()` against `maxrefs`). These defend against resource-exhaustion payloads
— a stream built entirely from allowed classes but structured with excessive graph depth, array
size, reference count, or raw byte volume, which a class-name allow-list alone does not prevent
since every class involved may be legitimately permitted.

</details>

**Q7.** Why does the recommended fix for QuizStakes's `LedgerEntry` persistence favor Avro or Protobuf over Java serialization, using the platform's own numbers?

<details><summary>Answer</summary>

At roughly 19.8M ledger entries written per day with 7 years of retention, a reader running today
routinely has to open rows written by a version of the service that no longer exists in any
deployed form. Avro and Protobuf both carry an explicit, versioned schema with defined
field-addition and field-removal resolution rules, so old rows remain readable under a schema that
has since evolved. Java serialization's compatibility story, covered in `02`, is comparatively
fragile — governed by `serialVersionUID` matching and default-value backfill with no clean removal
story — and, independent of compatibility, deserializing it always risks code execution, which a
7-year-retained financial ledger cannot accept as an ongoing exposure.

</details>

**Q8.** What changed for filters between JDK 9 and JDK 17, and what problem specifically did the JDK 17 change solve?

<details><summary>Answer</summary>

JDK 9 (JEP 290) introduced the filter mechanism itself: `ObjectInputFilter`, per-stream filters, and
the `jdk.serialFilter` process-wide property. JDK 17 (JEP 415) added the serial filter factory,
which is invoked at the construction of every `ObjectInputStream` with both the current process
filter and the stream's requested filter available to it. Before that, a per-stream filter and a
process-wide filter did not compose cleanly — one could effectively override the other rather than
both being enforced together. The factory lets a container or library combine the two deliberately,
for example enforcing a mandatory floor from the process filter while still layering a
context-specific filter on top for a particular call site.

</details>

## Open questions

1. Whether any specific JEP number should be cited for a future constructor-respecting replacement
   of `ObjectInputStream`'s default protocol. No such JEP is confirmed; settle by checking the
   OpenJDK JEP index before ever citing a number for this.

---

**Leaves covered:** 2.10.10–2.10.12 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 676
