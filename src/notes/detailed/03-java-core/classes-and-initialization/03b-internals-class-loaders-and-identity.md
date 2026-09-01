# 03 Java Core — Class loaders, identity and startup cost — INTERNALS (§3.6, 3.6.11–3.6.17)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Class-initialization locking and failure](03a-internals-class-init-locking-and-failure.md) · Next: [`final` semantics and constant folding](04-internals-final-and-constant-folding.md)

A class in a running JVM is not identified by its name. It is identified by a pair — the binary name and the loader that called `defineClass` on its bytes — and JVMS 21 writes that pair down as `<N, L_d>`. Every confusing symptom in this file falls out of that one fact: why `BonusRules` cannot be cast to `BonusRules`, why parent-first delegation forces frameworks to reach for a context class loader, why a redeploy leaks a whole rule set, and why `ClassNotFoundException` and `NoClassDefFoundError` are two different failures that a log line flattens into one. The file closes on the cost side of the same machinery: the class-loading-and-initialization bill every new instance pays before it serves a request, what CDS and AppCDS do about it on 21, and what JEP 483 changes in 24.

## 1. Class identity is the pair (name, defining loader) (3.6.13)

Picture two `RuleSetClassLoader` instances in one QuizStakes JVM, one holding the UK rule set jar and one holding the Irish one. Both jars contain a class file for `com.quizstakes.bonus.BonusRules`. Both loaders read those bytes and hand them to the JVM. What you now have in that JVM is not one class with two copies of its bytes — it is **two classes**, each with its own `Class` object, its own static fields, its own `<clinit>` that ran separately, and its own place in the type system. They share a name and nothing else. The type system treats them as unrelated as `Money` and `AccountId`.

### Why it exists

Because the alternative is a global namespace, and a global namespace makes the platform's most useful capability impossible. QuizStakes runs per-jurisdiction rule sets and per-brand white-label deployments; an application server hosts several applications; a hot redeploy swaps a new version of a rule set into a live JVM. Each of those needs two versions of the same fully-qualified name to coexist, with independent static state. If the JVM keyed classes on name alone, `com.quizstakes.bonus.BonusRules` could exist once per process, and the first loader to define it would win forever. Keying on `(name, defining loader)` is what buys isolation, versioning, plugin architectures and redeployment. The `ClassCastException` is the price of that capability, not a defect in it.

### The mechanism

`[SOURCE]` JVMS 21 §5.3, "Creation and Loading", states the initiating-versus-defining distinction verbatim:

> If L loads C directly, we say that L *defines* C or, equivalently, that L is the *defining loader* of C. Whether L loads C directly or indirectly, we say that L *initiates loading* of C, or, equivalently, that L is an *initiating loader* of C. Due to class loader delegation, the loader L1 that initiates loading at the Java Virtual Machine's request may not be the same as the loader L2 that completes loading by defining the class or interface.

And the notation the rest of the chapter uses:

> `<N, L_d>` — where N denotes the name of the class or interface and `L_d` denotes the defining loader of the class or interface.

Read the distinction precisely, because it is the one people get wrong. When your application-loader code says `new BonusRules()`, the application loader is the **initiating** loader. It delegates up; if the platform loader had found the class, the platform loader would be the **defining** loader, and the resulting class's identity would be `<com.quizstakes.bonus.BonusRules, platform>` — not `<com.quizstakes.bonus.BonusRules, app>`. `Class.getClassLoader()` returns the **defining** loader, always. There is no API that hands you the initiating loader, because the initiating loader is not part of the class's identity; it is only a record the JVM keeps in order to enforce loading constraints.

`[SOURCE]` Those constraints are JVMS 21 §5.3.4, and they are the reason two-loader trouble sometimes surfaces as a `LinkageError` at link time rather than a `ClassCastException` at run time:

> It is possible that when two different class loaders initiate loading of a class or interface denoted by N, the name N may denote a different class or interface in each loader. When a class or interface C = `<N1, L1>` makes a symbolic reference to a field or method of another class or interface D = `<N2, L2>`, the symbolic reference includes a descriptor specifying the type of the field, or the return and argument types of the method. It is essential that any type name N mentioned in the field or method descriptor denote the same class or interface when loaded by L1 and when loaded by L2. To ensure this, the Java Virtual Machine imposes loading constraints of the form `N^L1 = N^L2` during preparation (§5.4.2) and resolution (§5.4.3).

So the JVM does not merely permit two same-named classes to coexist; it actively polices the boundary between them, and throws a `LinkageError` the moment a descriptor would force the two to be treated as one.

The manifest assigns no diagram to this concept.

`[PROVE]` The reproduction, run on Oracle JDK 21.0.7 (aarch64, macOS). Two `RuleSetClassLoader` instances, both reading the same `BonusRules.class` bytes from the same directory, both **defining** rather than delegating for the `com.quizstakes.` prefix — child-first, which is exactly what a plugin loader does:

```java
package com.quizstakes.platform;

import java.io.IOException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;

/** Loads one jurisdiction's rule-set classes, child-first, so each jurisdiction defines its own. */
public final class RuleSetClassLoader extends URLClassLoader {

    private static final String RULE_SET_PACKAGE_PREFIX = "com.quizstakes.bonus.";

    private final String jurisdiction;

    public RuleSetClassLoader(String jurisdiction, Path ruleSetDirectory) throws IOException {
        super(jurisdiction + "-ruleset", new URL[] { ruleSetDirectory.toUri().toURL() }, null);
        this.jurisdiction = jurisdiction;
    }

    public String jurisdiction() {
        return jurisdiction;
    }

    @Override
    protected Class<?> loadClass(String binaryName, boolean resolve) throws ClassNotFoundException {
        synchronized (getClassLoadingLock(binaryName)) {
            Class<?> already = findLoadedClass(binaryName);
            if (already != null) {
                return already;
            }
            if (binaryName.startsWith(RULE_SET_PACKAGE_PREFIX)) {
                Class<?> defined = findClass(binaryName);   // this loader becomes the DEFINING loader
                if (resolve) {
                    resolveClass(defined);
                }
                return defined;
            }
            return super.loadClass(binaryName, resolve);    // everything else: parent-first
        }
    }
}
```

Driven by a probe that loads the same name through both loaders and then casts across:

```java
package com.quizstakes.platform;

import com.quizstakes.bonus.BonusRules;

import java.nio.file.Path;

public final class RuleSetIdentityProbe {

    public static void main(String[] args) throws Exception {
        Path ruleSets = Path.of(args[0]);
        try (RuleSetClassLoader ukRules = new RuleSetClassLoader("uk", ruleSets);
             RuleSetClassLoader ieRules = new RuleSetClassLoader("ie", ruleSets)) {

            Class<?> ukBonusRules = ukRules.loadClass("com.quizstakes.bonus.BonusRules");
            Class<?> ieBonusRules = ieRules.loadClass("com.quizstakes.bonus.BonusRules");

            System.out.println("same name?         " + ukBonusRules.getName().equals(ieBonusRules.getName()));
            System.out.println("same Class object? " + (ukBonusRules == ieBonusRules));
            System.out.println("assignable?        " + ukBonusRules.isAssignableFrom(ieBonusRules));
            System.out.println("uk defining loader " + ukBonusRules.getClassLoader().getName());
            System.out.println("ie defining loader " + ieBonusRules.getClassLoader().getName());

            Object ieInstance = ieBonusRules.getConstructor(String.class).newInstance("IE");
            BonusRules asAppType = (BonusRules) ieInstance;   // real checkcast against the app loader's copy
            System.out.println("cast succeeded: " + asAppType.jurisdiction());
        } catch (ClassCastException e) {
            System.out.println("ClassCastException: " + e.getMessage());
        }
    }
}
```

Measured output on JDK 21.0.7:

```
same name?         true
same Class object? false
assignable?        false
uk defining loader uk-ruleset
ie defining loader ie-ruleset
```

and, from the `checkcast` against the application loader's own copy of the class, the message that is the whole point of the leaf:

```
ClassCastException: class com.quizstakes.bonus.BonusRules cannot be cast to class
com.quizstakes.bonus.BonusRules (com.quizstakes.bonus.BonusRules is in unnamed module
of loader 'ie-ruleset' @33909752; com.quizstakes.bonus.BonusRules is in unnamed module
of loader 'app')
```

Three facts are proved rather than asserted: the two `Class` objects are distinct references (`==` is false) while their names are equal; `isAssignableFrom` is false in both directions, so the type system genuinely treats them as unrelated; and the message names the same class twice, disambiguated **only** by the parenthetical module-and-loader clause. That parenthetical is the diagnostic. Read the two loader names, and the cause is immediate. `[VERSION-TRAP]` On Java 8 the same cast produced only `java.lang.ClassCastException: com.quizstakes.bonus.BonusRules cannot be cast to com.quizstakes.bonus.BonusRules` with no loader information at all, which is why this failure has a folk reputation as unexplainable — on 8 it genuinely was, from the message alone.

**Insight:** class identity including the loader means a loader and every class it defined are one unit for garbage collection. A `Class` strongly references its defining loader (`getClassLoader()` must keep working), and a loader strongly references every class it defined, so the whole graph — loader, classes, their static fields, and everything those static fields reach — is collectible only as a set, and only when nothing outside it is reachable. One leaked reference into a discarded `RuleSetClassLoader` — a `ThreadLocal` never cleared on a pooled `stake-reservation-3` thread, a JDBC driver registered in `DriverManager`, a shutdown hook, a JMX MBean — pins the entire rule set in metaspace. Redeploy twenty times and you have twenty rule sets resident. That is the classic redeploy metaspace leak, and metaspace, class unloading and the GC of loaders belong to guide **06 JVM internals** `[X-REF 06]`.

`[TRAP]` **Pitfall:** the wrong belief is "two classes with the same fully-qualified name are the same class, so this must be a JVM bug." The symptom is `ClassCastException` naming one class twice, or a `LinkageError` at link time, or an `instanceof` that returns false against a type the object visibly is, or reflection succeeding where a direct cast fails. The fix is never to cast — it is to find why the name is defined twice, and there are only three common causes: (a) the same jar is on both the parent classpath and the child's, so parent-first finds one copy and child-first finds the other; (b) a hot redeploy left the old loader alive with live references into it; (c) an application server splits shared and per-application classpaths and the same library sits in both. Where two loaders genuinely must coexist, the only supported bridge is a **shared interface defined by a common ancestor loader** — put `BonusRuleSet` on the parent classpath and keep it out of the child's, so both children's implementations implement the *same* interface class, and pass values across as that interface. A two-loader `ClassCastException` and an erasure-induced one read identically in a log; the erasure variant is `../generics/03-internals-erasure.md` (diagram D-105), and the tell is that the erasure one names two *different* class names.

> A run-time class is the pair `<N, L_d>` of its binary name and its defining loader; two loaders that each define the same bytes produce two mutually unassignable types.

## 2. Delegation, and the three loaders that actually exist on Java 21 (3.6.12)

Three loaders, arranged as a chain of parents, and a request that walks **up** the chain before anything walks down. Bootstrap sits at the top with no parent and is not even a Java object — it is inside the VM, and every API that wants to name it uses `null`. Below it the platform loader owns the Java SE APIs and the JDK's own runtime classes. Below that the application loader owns your classpath and module path. `RuleSetClassLoader` from section 1 hangs off one of them, or off nothing at all.

### Why it exists

Parent-first delegation exists to make the platform's own types unforgeable. If a request for `java.lang.String` were answered by whichever loader found it first, any classpath entry containing a hostile `java/lang/String.class` would silently replace the real one, and every security invariant in the platform would evaporate. Delegating upward first guarantees that a name the parent can supply is *always* answered by the parent, so `String`, `Object` and `Class` are defined exactly once, by the bootstrap loader, for the life of the JVM. Everything else — the cast confusion, the context-class-loader workaround — is a consequence of that one non-negotiable rule.

### The mechanism

`[SOURCE]` `ClassLoader`'s own Java 21 class documentation states the model and the null representation verbatim:

> The `ClassLoader` class uses a delegation model to search for classes and resources. Each instance of `ClassLoader` has an associated parent class loader. When requested to find a class or resource, a `ClassLoader` instance will usually delegate the search for the class or resource to its parent class loader before attempting to find the class or resource itself.

> Bootstrap class loader. It is the virtual machine's built-in class loader, typically represented as `null`, and does not have a parent.

`[SOURCE]` And the algorithm itself, from `ClassLoader.loadClass(String name, boolean resolve)`:

> Loads the class with the specified binary name. The default implementation of this method searches for classes in the following order:
>
> 1. Invoke `findLoadedClass(String)` to check if the class has already been loaded.
> 2. Invoke the `loadClass` method on the parent class loader. If the parent is `null` the class loader built into the virtual machine is used, instead.
> 3. Invoke the `findClass(String)` method to find the class.
>
> If the class was found using the above steps, and the `resolve` flag is true, this method will then invoke the `resolveClass(Class)` method on the resulting `Class` object.

Every clause earns its place. Step 1 is what makes loading idempotent per loader — a second request for the same name returns the same `Class` object, which is why a loader can never define the same name twice. Step 2 is the parent-first rule, and the "if the parent is `null`" clause is how a loader constructed with `super(name, urls, null)` reaches bootstrap directly, skipping platform and application entirely — that is what `RuleSetClassLoader` did in section 1, and it is why the rule-set loader could not see the application's `BonusRules` even by accident. Step 3, `findClass`, is the only step that **defines** anything, and it is the step the javadoc tells you to override rather than overriding `loadClass` itself. Section 1 overrode `loadClass` precisely because it wanted to *break* step 2's ordering; that is the deliberate exception, not the pattern.

`[VERSION-TRAP]` The hierarchy is **bootstrap → platform → application**. It is not bootstrap/extension/application, and it has not been since Java 9. `[SOURCE]` JEP 220, "Modular Run-Time Images", Status Closed/Delivered, **Release 9**, lists under *Removed: The extension mechanism*:

> The mechanism was defined in terms of a path-like system property, `java.ext.dirs`, and a default value for that property composed of `$JAVA_HOME/lib/ext` and a platform-specific system-wide directory […]. It worked in much the same manner as the endorsed-standards mechanism except that JAR files placed in an extension directory were loaded by the run-time environment's **extension class loader**, which is a child of the bootstrap class loader and the parent of the system class loader […]

That loader is gone and the platform class loader took its structural position. Measured on Oracle JDK 21.0.7, the removal is enforced at launch, not merely undocumented:

```
$ java -Djava.ext.dirs=/tmp -version
-Djava.ext.dirs=/tmp is not supported.  Use -classpath instead.
Error: Could not create the Java Virtual Machine.
```

Measured hierarchy on the same JDK:

| Loader | Accessor | `getName()` | Parent | Owns |
|---|---|---|---|---|
| Bootstrap | none — represented as `null` | n/a | none | `java.base` core types; `String.class.getClassLoader()` measured `null` |
| Platform | `ClassLoader.getPlatformClassLoader()` | `platform` | bootstrap (`getParent()` measured `null`) | Java SE APIs and JDK runtime classes; `javax.sql.DataSource.class.getClassLoader()` measured the platform loader |
| Application (system) | `ClassLoader.getSystemClassLoader()` | `app` | platform | the class path and module path; measured as the defining loader of the probe class itself |

`[TRAP]` `getParent()` returning `null` for the bootstrap loader is not an error case and not an absence of information — it *is* the bootstrap loader. Any code that walks the parent chain, or logs a loader, must handle `null` as a value rather than a failure; `String.class.getClassLoader()` returns `null` on every conforming JVM, so `someClass.getClassLoader().getResource(name)` is a latent `NullPointerException` for any platform or JDK type. The correct form for resource lookup that must also work for bootstrap-defined classes is the static `ClassLoader.getSystemResource(name)`, or `Class.getResource(name)`, which routes through the right loader itself.

The manifest assigns no diagram to this concept.

**The context class loader.** Parent-first delegation has one structural hole: a class defined by a *parent* loader can never see a class visible only to a *child*. `ServiceLoader`, JDBC and JPA all live in that hole. `java.sql.DriverManager` is defined by the platform loader; a PostgreSQL driver sits on the application classpath, invisible to the platform loader by construction. `Thread.getContextClassLoader()`/`setContextClassLoader()` is the escape hatch: a mutable, per-thread loader reference that framework code consults instead of its own `getClass().getClassLoader()`, letting a parent-defined framework reach downward.

`[SOURCE]` `ServiceLoader.load(Class)` in the Java 21 javadoc:

> Creates a new service loader for the given service type, using the current thread's context class loader. An invocation of this convenience method of the form `ServiceLoader.load(service)` is equivalent to `ServiceLoader.load(service, Thread.currentThread().getContextClassLoader())`

> API Note: Service loader objects obtained with this method should not be cached VM-wide. For example, different applications in the same VM may have different thread context class loaders. […] Memory leaks can also arise.

The two-argument `ServiceLoader.load(Class, ClassLoader)` takes the loader explicitly and does not touch the context class loader — which makes it the form to prefer whenever you know which loader you mean. Spring's own `ClassUtils` follows the same discipline, resolving a loader in a defined order rather than assuming either one. QuizStakes usage, complete:

```java
package com.quizstakes.platform;

import java.nio.file.Path;
import java.util.List;
import java.util.ServiceLoader;

/** Discovers per-jurisdiction bonus rule sets from an isolated loader, without touching the caller's context loader permanently. */
public final class JurisdictionRuleSets {

    public interface BonusRuleSet {
        String jurisdiction();
        long grantCapMinorUnits();
    }

    public static List<BonusRuleSet> discover(String jurisdiction, Path ruleSetDirectory) throws Exception {
        Thread current = Thread.currentThread();
        ClassLoader previous = current.getContextClassLoader();
        try (RuleSetClassLoader loader = new RuleSetClassLoader(jurisdiction, ruleSetDirectory)) {
            current.setContextClassLoader(loader);
            // Explicit loader: does not depend on the context loader being set at all.
            return ServiceLoader.load(BonusRuleSet.class, loader)
                    .stream()
                    .map(ServiceLoader.Provider::get)
                    .toList();
        } finally {
            current.setContextClassLoader(previous);   // pooled threads outlive this call
        }
    }
}
```

`[TRAP]` **Pitfall:** the wrong belief is that setting the context class loader is a scoped operation. It is not — it is a mutable field on a `Thread` object, and QuizStakes runs its request path on pooled threads (`http-nio-8443-exec-7`, `payment-run-worker`). Set it and forget to restore it, and the next unrelated task on that thread inherits a loader that may already have been closed, producing a `ClassNotFoundException` in code that never mentions class loading — or pins the discarded loader in metaspace for as long as the pool thread lives, which is the leak the `ServiceLoader` javadoc warns about above. The fix is the `try`/`finally` restore shown, without exception. Modules, the module path, `exports`/`opens`, strong encapsulation and `--add-opens` are where the platform loader and module resolution actually meet, and they are `../language-substrate/02-packages-modules-annotations.md` (diagram D-060); the one-paragraph version is that a class in a *named* module is resolved through its module's reads-edges before its loader's classpath, so on the module path the loader chain is not the whole story.

> Delegation is parent-first by default — check-loaded, ask the parent, then define locally — over the chain bootstrap (`null`) → platform → application; the context class loader is a per-thread override that lets parent-defined framework code reach child-visible implementations.

## 3. `ClassNotFoundException` versus `NoClassDefFoundError` (3.6.11)

Two log lines that look like the same problem and never are. One says "I asked, by name, at run time, and the answer was no" — a question that was allowed to fail. The other says "the compiler already proved this type existed, and it is not here now" — a promise that was broken.

### Why it exists as a distinction

`Class.forName("com.quizstakes.psp.WorldpayAdapter")` is a *query*. Queries can legitimately have no answer: an optional PSP adapter, a plugin that was not deployed, a driver class named in configuration. The platform therefore makes that failure a **checked exception** — the caller is forced to consider it. By contrast, when `javac` compiled `PaymentService` against `BonusRules`, the resulting class file contains a symbolic reference to `BonusRules` in its constant pool, and there is no source-level place to handle its absence, because at compile time it was not absent. That failure is an `Error`: the JVM's own view of the world is inconsistent, and no local `catch` can repair it.

### The mechanism

`[X-REF 06]` Placement in the hierarchy first, because it settles which is catchable by convention and which is not: `ClassNotFoundException extends ReflectiveOperationException extends Exception` — measured on JDK 21.0.7, the supertype chain printed `java.lang.ReflectiveOperationException -> java.lang.Exception`. `NoClassDefFoundError extends LinkageError extends Error`. The full exception hierarchy, and `LinkageError`'s place in it, is `../exceptions/01-basics.md` (diagram D-053).

`[SOURCE]` JVMS 21 §5.3.1 spells out how one becomes the other:

> If no purported representation of C is found, the bootstrap class loader throws a `ClassNotFoundException`. The process of loading and creating C then fails with a `NoClassDefFoundError` whose cause is the `ClassNotFoundException`.

That sentence is the whole relationship: the loader's *lookup* failure is a `ClassNotFoundException`, and when the JVM was performing that lookup on behalf of *linkage*, it wraps it into a `NoClassDefFoundError`. Same missing file, two different exceptions, decided entirely by who asked.

There are therefore **three** distinct situations, not two, and conflating them is what makes the leaf worth a section. The third is a failed `<clinit>` — the class was found and linked, its initializer threw, and every subsequent use of that class gets a `NoClassDefFoundError` for a class that is physically present.

| | Thrown by | Supertype | Root cause | What to do |
|---|---|---|---|---|
| `ClassNotFoundException` | `Class.forName` / `ClassLoader.loadClass` — an explicit lookup you wrote | `ReflectiveOperationException` → `Exception` (checked) | No binary representation of that name is visible to the loader you used | Handle it — it is a legitimate answer. Check the name spelling and *which loader* you asked |
| `NoClassDefFoundError` — **linkage** | The JVM, resolving a symbolic reference from a constant pool | `LinkageError` → `Error` | The class was on the compile classpath and is absent from the run-time classpath | Fix the deployment: missing/shaded/version-skewed jar, `provided` scope, module not on the path |
| `NoClassDefFoundError` — **failed initialization** | The JVM, on any use of a class whose `<clinit>` already threw | `LinkageError` → `Error` | The class exists and is linked; its static initializer failed earlier | Find the *original* `ExceptionInInitializerError`. Owned by `03a-internals-class-init-locking-and-failure.md` |

`[VERSION-TRAP]` The third row used to be the hardest failure in Java to diagnose, because the second and subsequent `NoClassDefFoundError` carried no trace of the initializer that actually failed. That was JDK-8048190, fixed in **JDK 18** and backported to **17.0.7, 11.0.19 and 8u341**: on JDK 21 the failed-initialization `NoClassDefFoundError` *does* carry a reconstructed `Caused by:`. The measurement establishing that is in `03a`; do not carry the pre-fix folklore into a JDK 21 answer.

The manifest assigns no diagram to this concept.

Measured on Oracle JDK 21.0.7, both of this section's failures reproduced from one program. `BonusService` calls `Class.forName` on a name that was never deployed, and separately does `new BonusRules()` against a class compiled against and then deleted from the run-time classpath:

```java
package com.quizstakes.bonus;

public final class BonusService {

    /** An optional PSP-specific rule-set adapter: absence is a legitimate answer. */
    public static Class<?> optionalAdapter(String binaryName) {
        try {
            return Class.forName(binaryName);
        } catch (ClassNotFoundException e) {
            System.out.println("ClassNotFoundException: " + e.getMessage());
            return null;
        }
    }

    /** A hard compile-time dependency: absence is a broken deployment. */
    public static long grantCapMinorUnits() {
        BonusRules rules = new BonusRules();   // symbolic reference resolved at link time
        return rules.grantCapMinorUnits();
    }

    public static void main(String[] args) {
        optionalAdapter("com.quizstakes.bonus.MissingRuleSet");
        System.out.println("cap=" + grantCapMinorUnits());
    }
}
```

The lookup path printed exactly:

```
ClassNotFoundException: com.quizstakes.bonus.MissingRuleSet
```

Then, with `BonusRules.class` removed from the run-time classpath but `BonusService.class` untouched:

```
Exception in thread "main" java.lang.NoClassDefFoundError: BonusRules
	at BonusService.main(BonusService.java:14)
Caused by: java.lang.ClassNotFoundException: BonusRules
	at java.base/jdk.internal.loader.BuiltinClassLoader.loadClass(BuiltinClassLoader.java:641)
	at java.base/jdk.internal.loader.ClassLoaders$AppClassLoader.loadClass(ClassLoaders.java:188)
	at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:526)
	[one further frame, truncated by the JVM trace printer itself]
```

Note what the `Caused by:` proves: it is JVMS §5.3.1's wrapping, visible. The `ClassNotFoundException` really is inside the `NoClassDefFoundError`, and its stack frames are the loader's, not yours. That nesting is the field diagnostic — a linkage `NoClassDefFoundError` whose cause is a `ClassNotFoundException` in `BuiltinClassLoader.loadClass` is a **deployment** problem; a `NoClassDefFoundError` whose cause is anything else is a **failed-initialization** problem and belongs to `03a`.

`[TRAP]` **Pitfall:** the wrong belief is "I catch `ClassNotFoundException` around this, so a missing class is handled." The symptom is a `NoClassDefFoundError` propagating straight past a perfectly good `catch (ClassNotFoundException e)` and killing the request thread, because the missing class was reached through a normal `new`/field/method reference rather than through the reflective lookup that the `catch` guards. The fix is to be honest about which failure mode a call site can actually produce: reflective lookup produces the checked exception; a compiled-in dependency produces the `Error`. If a dependency is genuinely optional, it must be reached *only* reflectively behind an interface the caller owns, never referenced directly, or `javac` will emit a constant-pool entry that turns its absence into a `LinkageError` you cannot handle. Translation and diagnosis discipline for a `LinkageError` you cannot fix at the call site is `../exceptions/02-in-practice.md`.

**Interview:** "What is the difference between `ClassNotFoundException` and `NoClassDefFoundError`?" is asked constantly, and the answer that separates candidates is the *three*-way split, not the two-way one — checked exception from an explicit lookup, `LinkageError` from a resolution failure, and `LinkageError` from a failed `<clinit>` on a class that is physically present. Add the JVMS §5.3.1 wrapping relationship and the JDK-18 `Caused by:` fix, and the answer is complete in under ninety seconds.

> `ClassNotFoundException` is a checked exception reporting that a lookup you performed found nothing; `NoClassDefFoundError` is a `LinkageError` reporting that the JVM could not resolve a reference the compiler had already validated, or that the class's initializer had already failed.

## 4. The holder-class idiom, and why it is the cheapest correct lazy singleton (3.6.15)

The trick is to have no trick. Put the singleton in a nested class whose *only* purpose is to hold it, and the accessor becomes a plain static field read. There is no null check, no lock, no `volatile`, no double read — the JVM's own class-initialization procedure supplies exactly-once semantics and the memory ordering, and it does so for free because that procedure has to run anyway the first time anything touches the holder class.

### Why it exists

Introduced at BASICS depth in `01d-class-initialization-triggers.md` (diagrams D-039, D-040) — go there for the introduction and the triggers. The INTERNALS question is narrower: why is this the *cheapest correct* form, rather than merely a tidy one? The competition is real. Eager `static final` initialization is correct but pays the construction cost at class-initialization time whether the singleton is ever used or not. A `synchronized` accessor is correct but takes a monitor on every call, forever, to protect a window that closes microseconds after startup. Double-checked locking with `volatile` is correct on Java 5 and later and pays only a volatile read in steady state, but it is three times the code and was **genuinely broken before Java 5**, because the pre-JSR-133 memory model permitted a thread to observe a non-null reference to a partially constructed object. An enum singleton is correct and serialization-safe but cannot take constructor arguments and is initialized eagerly on first access to the enum type.

### The mechanism

`[SOURCE]` `[PROVE]` The correctness comes from one sentence of JVMS 21 §5.5's initialization procedure:

> If the `Class` object for C indicates that C has already been initialized, then no further action is required. Release LC and complete normally.

That is the exactly-once guarantee, spelled out: initialization runs at most once per class per loader, under a per-class lock, with every other thread blocking until it completes. So `Holder.INSTANCE` is assigned exactly once, by exactly one thread, and every thread that reads it afterwards is guaranteed by the same procedure to see the fully constructed object. No double-checked locking is needed because the JVM already performs the check-lock-check-initialize dance on your behalf, correctly, in the VM. The twelve-step procedure and the four `Class` states are `03a-internals-class-init-locking-and-failure.md`'s territory.

`[SOURCE]` The *cost* half of the proof is the immediately following permission in §5.5:

> A Java Virtual Machine implementation may optimize this procedure by eliding the lock acquisition in step 1 (and release in step 4/5) when it can determine that the initialization of the class has already completed, provided that, in terms of the Java memory model, all happens-before orderings (JLS §17.4.5) that would exist if the lock were acquired, still exist when the optimization is performed.

Read it as what it is: a **permission granted to the implementation**, not an observed HotSpot behaviour — a conforming JVM need not elide anything. The load-bearing clause is the proviso. The happens-before edges that the lock would have created must *still exist* after the elision. So the elision cannot be used to weaken the guarantee; it removes the lock and keeps the ordering. That is precisely what makes the holder idiom cheapest *and* correct at the same time: correctness comes from the initialization guarantee, and the steady-state cost may legally fall to a bare field read because the specification lets the implementation drop the check once initialization has completed.

`[PROVE]` The bytecode confirms there is nothing left to elide in *your* code. Measured with `javap -c -p` on Oracle JDK 21.0.7:

```
  public static FundsLedger instance();
    Code:
       0: getstatic     #7    // Field FundsLedger$Holder.INSTANCE:LFundsLedger;
       3: areturn
```

Two instructions. No `ifnull`, no `monitorenter`, no `dup`, no local. The lazy-initialization *logic* lives entirely in the holder's `<clinit>`, which the same run showed as `new`/`dup`/`invokespecial`/`putstatic`/`return`, and which the JVM runs once. Compare the alternatives, same JDK, same `javap` invocation:

| Strategy | Accessor bytecode (measured) | Steady-state cost | Correct? | Cost / escape hatch |
|---|---|---|---|---|
| Eager `static final` | `getstatic; areturn` (2) | field read | Yes | Pays construction at class-init whether used or not; escape hatch is the holder idiom |
| Holder class | `getstatic; areturn` (2) | field read; lock elidable per §5.5 | Yes | One extra class in metaspace per singleton; that is the whole bill |
| `synchronized` accessor | `getstatic; ifnonnull; new; dup; invokespecial; putstatic; getstatic; areturn` (8) **plus** `ACC_SYNCHRONIZED` monitor on every entry and exit | monitor acquire/release per call | Yes | Uncontended monitors are cheap but never free; escape hatch is the holder idiom |
| Double-checked locking with `volatile` | 21 instructions including `monitorenter`/`monitorexit` and a **two-entry exception table** | one volatile read | Yes on Java 5+ | Broken before Java 5; easy to get wrong (drop `volatile` and it silently breaks); escape hatch is the holder idiom |
| `enum` singleton | `getstatic; areturn` (2) | field read | Yes, and serialization-safe | No constructor arguments; eager on first access to the enum type |

The bytecode counts are the argument. The holder idiom ties the *cheapest* option in the table while being the only lazy one that needs no memory-model reasoning from the author at all.

`[PROVE]` And it really is lazy, measured rather than assumed. `-Xlog:class+load=info` on JDK 21.0.7, on a program that first touches the `FundsLedger.class` literal and only later calls `instance()`:

```
[0.022s][info][class,load] FundsLedger source: file:/private/tmp/qsholder/
class literal only: FundsLedger
--- now calling instance() ---
[0.025s][info][class,load] FundsLedger$Holder source: file:/private/tmp/qsholder/
```

`FundsLedger` loads when the class literal is evaluated; `FundsLedger$Holder` does not load until `instance()` executes its `getstatic`, three milliseconds later in the log. A class literal is not an initialization trigger, and `getstatic` on another class's field is — the six triggers are enumerated in `03-internals-class-loading-and-init.md` (diagram D-107).

The manifest assigns no diagram to this concept.

`[BUILD]` The complete, compiling article — a generic holder so the pattern is reusable, plus the concrete QuizStakes singleton:

```java
package com.quizstakes.ledger;

import java.math.BigDecimal;
import java.util.Currency;
import java.util.EnumMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

public record Money(BigDecimal amount, Currency currency) { }

enum LedgerPosition {
    CLIENT_CASH_AVAILABLE, CLIENT_CASH_RESERVED,
    CLIENT_BONUS_AVAILABLE, CLIENT_BONUS_RESERVED,
    SUSPENSE, PSP_RECEIVABLE, BANK_SETTLEMENT,
    HOUSE_REVENUE, PROMOTIONAL_EXPENSE, FEES, CHARGEBACK_LOSS
}

/**
 * Process-wide ledger position registry. Construction reads configuration and pre-sizes
 * eleven position accumulators, so it is worth deferring until something actually posts.
 */
public final class FundsLedger {

    private final Map<LedgerPosition, AtomicLong> minorUnitsByPosition;
    private final Currency baseCurrency;

    private FundsLedger(Currency baseCurrency) {
        this.baseCurrency = baseCurrency;
        this.minorUnitsByPosition = new EnumMap<>(LedgerPosition.class);
        for (LedgerPosition position : LedgerPosition.values()) {
            minorUnitsByPosition.put(position, new AtomicLong(0L));
        }
    }

    /** The whole idiom: a nested class that exists only to hold the instance. */
    private static final class Holder {
        static final FundsLedger INSTANCE = new FundsLedger(Currency.getInstance("GBP"));
    }

    /** Compiles to exactly `getstatic; areturn` — no null check, no lock, no volatile. */
    public static FundsLedger instance() {
        return Holder.INSTANCE;
    }

    public Currency baseCurrency() {
        return baseCurrency;
    }

    public long post(LedgerPosition position, long minorUnits) {
        return minorUnitsByPosition.get(position).addAndGet(minorUnits);
    }

    public long balanceMinorUnits(LedgerPosition position) {
        return minorUnitsByPosition.get(position).get();
    }
}

/**
 * The same idiom generalised: one holder class per parameterisation, still lazy,
 * still exactly-once, and the accessor is still a single field read after the first call.
 */
final class LazyHolder<T> {

    private final java.util.function.Supplier<T> factory;
    private volatile T value;

    private LazyHolder(java.util.function.Supplier<T> factory) {
        this.factory = factory;
    }

    static <T> LazyHolder<T> of(java.util.function.Supplier<T> factory) {
        return new LazyHolder<>(factory);
    }

    T get() {
        T local = value;
        if (local == null) {
            synchronized (this) {
                local = value;
                if (local == null) {
                    value = local = factory.get();
                }
            }
        }
        return local;
    }
}
```

`[TRAP]` **Pitfall:** the `LazyHolder<T>` above is deliberately included to show the cost of generality, and it is the trap. A *generic* lazy holder cannot use the class-initialization guarantee at all, because there is one `LazyHolder` class regardless of how many instances you make — so it is forced back into double-checked locking, `volatile`, and a monitor. The holder-class idiom's cheapness is not portable to an *instance*-level lazy field; it is available only for a **static** singleton, because its guarantee is the per-class initialization lock. Reaching for a generic wrapper to "reuse the pattern" silently trades two instructions for twenty-one. If you need instance-level laziness on Java 21, double-checked locking with `volatile` is the honest answer; the API that would replace it is 3.6.16's subject and does not exist on 21.

> The holder-class idiom is the cheapest correct lazy singleton because its correctness is the JVM's per-class initialization guarantee rather than any code you wrote, and its steady-state accessor compiles to `getstatic; areturn` with no check of any kind.

## Supporting facts

### `Class.forName`'s loader argument and the identity it decides (3.6.14)

The `Class.forName` versus `loadClass` distinction is introduced in `01d-class-initialization-triggers.md`; the INTERNALS layer is the **three-argument** form's loader parameter, because that parameter is what section 1's identity pair is made of. `Class.forName(name, initialize, loader)` initiates loading through the loader you pass, so the resulting `Class` object's identity is `<name, whichever loader ultimately defined it>` — which may be the loader you passed, or any of its ancestors, depending on where delegation landed. Passing the wrong loader is exactly how a service ends up holding a `Class` object that is name-identical to and type-incompatible with the one the rest of the code compiled against. `[SOURCE]` Java 21 javadoc, verbatim across the four entry points:

| Call | Initializes? | On failure | Loader used |
|---|---|---|---|
| `Class.forName(String)` | Yes — "A call to `forName("X")` causes the class named `X` to be initialized." | `ClassNotFoundException` (checked) | The caller's own defining loader |
| `Class.forName(String, boolean, ClassLoader)` | Only if asked — "The class is initialized only if the `initialize` parameter is `true` and if it has not been initialized earlier." | `ClassNotFoundException` (checked) | Exactly the loader you pass; `null` means bootstrap |
| `ClassLoader.loadClass(String)` | No — "Invoking this method is equivalent to invoking `loadClass(name, false)`." | `ClassNotFoundException` (checked) | The receiver, delegating parent-first |
| `Class.forName(Module, String)` (Java 9+) | No — "It does not link the class, and does not run the class initializer." | Returns `null` — "This method returns `null` on failure rather than throwing a `ClassNotFoundException`" | The given module's loader |

The `resolve=false` in `loadClass`'s definition is the whole mechanism: no resolution, therefore no initialization, therefore a `Class` object whose static fields are all still at their default values and whose `<clinit>` has never run. That is the classic surprise — `loadClass` where `forName` was needed hands back a class that looks loaded and behaves as if its configuration were never read. The fourth row is the genuinely non-obvious one: `Class.forName(Module, String)` is the only member of the family that reports failure by returning `null`, so a null check replaces a `catch` there, and forgetting it produces a `NullPointerException` rather than a `ClassNotFoundException`. Reflection, `Class` objects and `getDeclaredX` versus `getX` are `../reflection/02-reflection.md` (table D-087).

### Lazy static final fields: a draft, and the API that actually shipped (3.6.16)

`[RESEARCH]` The problem is real and narrow. Today the only way to get a JIT-trusted constant is a `static final` field initialised at class-initialization time, so you must choose between eager initialization and losing the constant folding. `[SOURCE]` The OpenJDK draft states it precisely — JEP draft **8209964, "Lazy Static Final Fields"**, owner John Rose, Type Feature, Scope JDK, **Status: Draft**, created 2018, last updated 2023, never promoted to a mainline JEP number:

> Class initializers are coarse-grained compared to mechanisms using bootstrap methods, because their contract is to run *all* initialization code for a whole class, rather than *some* initialization that may pertain to a particular field of that class. […] It only takes one extra-complicated static field in a class to make all fields non-optimizable.

That is exactly why the holder-class idiom exists: it buys per-field granularity by paying one extra class per constant. The draft names the internal mechanism directly — "Since Java 7 they have been an increasingly important part of JDK internals, expressed via the internal `@Stable` annotation" — and `@Stable`, JIT constant folding and `final` field semantics are `04-internals-final-and-constant-folding.md` (diagram D-122, table D-123). **The insight tying the two files together:** `@Stable` is the JDK-internal mechanism that this line of work exposes safely to application code.

The leaf's phrasing — "the JEP draft" — is stale, because the work that shipped took a **library** route rather than a language route. `[SOURCE]` Verified metadata: **JEP 502, "Stable Values (Preview)"**, previewed in JDK 25; then **JEP 526, "Lazy Constants (Second Preview)"**, authors Per Minborg and Maurizio Cimadamore, Status Closed/Delivered, **Release 26**, issue 8359894, whose History says "This API previewed in JDK 25 via JEP 502" and which renamed `StableValue` to `LazyConstant`; then **JEP 531, "Lazy Constants (Third Preview)"**, same authors, Status Closed/Delivered, **Release 27**, issue 8376595, which adds `Set.ofLazy` and removes `isInitialized` and `orElse`. JEP 526's summary, verbatim:

> Introduce an API for lazy constants, which are objects that hold unmodifiable data. Lazy constants are treated as true constants by the JVM, enabling the same performance optimizations that are enabled by declaring a field `final`. Compared to `final` fields, however, lazy constants offer greater flexibility as to the timing of their initialization. This is a preview API.

Both JEP 526 and JEP 531 list as an explicit **non-goal** "to enhance the Java programming language with a means to declare lazy fields" — so the draft's language route is, for now, abandoned in favour of a library type. None of this exists on Java 21: on 21 the holder-class idiom of section 4 is the entire toolkit, and its cost is one extra class per lazily-initialised constant.

### Startup cost of class initialization, CDS/AppCDS on 21, and JEP 483 in Java 24 (3.6.17)

`[RESEARCH]` `[X-REF 06]` Startup time is a **capacity** concern for QuizStakes, not a developer-convenience one, and the shape of the argument is the traffic profile. Concurrent sessions run 14k steady and 55k at peak; registrations run 12k/day steady and 40k/day at peak. Absorbing a near-4x session swing means adding instances *under load*, and every instance added pays the full class-loading-and-initialization bill — scan jars, parse class files, verify, prepare, resolve, then run every `<clinit>` — before it serves its first request. If that bill is measured in seconds and the peak arrives in minutes, the autoscaler is structurally behind the traffic. **Do not quote a QuizStakes startup figure — none has been measured.** What to measure, per `../language-substrate/05-internals-observability.md` and guide **06**: class count and load timestamps via `-Xlog:class+load=info`, initialization time via `-Xlog:class+init`, and the whole startup profile under JFR.

Scale of the bill, measured on Oracle JDK 21.0.7: a program that only prints its loaders loaded **627 classes**, of which **604** came from the shared archive rather than from disk. `[SOURCE]` For a real server application, JEP 483 states that "Spring PetClinic, version 3.2.0 […] loads and links about 21,000 classes at startup."

`[BUILD]` CDS and AppCDS flags, each verified on JDK 21.0.7 rather than recalled — `java -XX:+PrintFlagsFinal -version` reported `SharedArchiveFile`, `ArchiveClassesAtExit`, `DumpLoadedClassList`, `SharedClassListFile`, `ExtraSharedClassListFile` and `AutoCreateSharedArchive`, all `{JVMCI product} {default}`, and `java -X` reported `-Xshare:auto` (default), `-Xshare:off`, `-Xshare:on`. A default archive ships with the JDK — `lib/server/classes.jsa`, 14,647,296 bytes on this install — which is why `java -version` is already faster than it would otherwise be; `-Xlog:cds=info` confirmed it being mapped. `[SOURCE]` JEP 483 corroborates: "builds of JDK 12 and later include a built-in CDS archive containing the metadata of over a thousand commonly-used JDK classes. CDS is, therefore, ubiquitous, even though many Java developers have never heard of it and few have used it directly."

The AppCDS round trip, run end to end on JDK 21.0.7 against a jar classpath:

```
$ java -XX:ArchiveClassesAtExit=qs.jsa -cp qs.jar LazinessProbe
$ java -XX:SharedArchiveFile=qs.jsa -Xlog:class+load=info -cp qs.jar LazinessProbe
[0.021s][info][class,load] FundsLedger source: shared objects file (top)
[0.024s][info][class,load] FundsLedger$Holder source: shared objects file (top)
```

Two things in that output matter. First, application classes really are served from the archive, not from the jar — that is the win, and its cost is a training run plus an archive file to version alongside the artefact. Second, and this is the connection back to this file's own subject: `FundsLedger$Holder` still appears at the `instance()` call, three milliseconds after `FundsLedger`. **CDS archives loaded-and-linked form; it does not archive initialization.** The holder idiom is exactly as lazy from the archive as from disk.

`[SOURCE]` `[VERSION-TRAP]` What arrives after 21: **JEP 483, "Ahead-of-Time Class Loading & Linking"**, authors Ioi Lam, Dan Heidinga and John Rose, Type Feature, Scope JDK, Status Closed/Delivered, **Release 24**, component hotspot/runtime, issue 8315737, relating to JEP 515 and JEP 514. Summary, verbatim:

> Improve startup time by making the classes of an application instantly available, in a loaded and linked state, when the HotSpot Java Virtual Machine starts. Achieve this by monitoring the application during one run and storing the loaded and linked forms of all classes in a cache for use in subsequent runs. Lay a foundation for future improvements to both startup and warmup time.

Its own figures, attributed: a short Stream-using program ran 0.031s on JDK 23 and 0.018s on JDK 24 with an AOT cache — 42%, with an 11.4 MB cache; Spring PetClinic 3.2.0 ran 4.486s on JDK 23 and 2.604s on JDK 24 — also 42%, with a 130 MB cache. The JEP's own breakdown shows CDS-style reading and parsing alone accounted for +13% on the short program and +33% on PetClinic, with loading and linking supplying the rest.

Two things to state carefully. **First, this is JDK 24, not 21** — on the target version it does not exist; what you have on 21 is CDS and AppCDS, and the new `-XX:AOT*` options are, per the JEP, "for the most part at this time, macros for existing CDS options such as `-Xshare`, `-XX:DumpLoadedClassList`, and `-XX:SharedArchiveFile`." **Second, on whether initialization is cached:** the JEP's Description states only that "the reading, parsing, loading, and linking work that HotSpot would usually do just-in-time […] is shifted ahead-of-time," and its Motivation lists the execution of static initializers as a *separate* third activity that the Description never claims to shift. The JEP does not state that `<clinit>` execution is cached, and I am not inferring that it is not — see Open questions. Also explicitly a non-goal: "It is not a goal to cache classes that are loaded by user-defined class loaders. Only classes loaded from the class path, the module path, and the JDK itself, by the JDK's built-in class loaders, can be cached." A `RuleSetClassLoader` gets no benefit.

## Pitfalls

### Reading `ClassCastException: BonusRules cannot be cast to BonusRules` as a JVM bug

**Wrong**

```java
Class<?> ieBonusRules = ieRules.loadClass("com.quizstakes.bonus.BonusRules");
Object ieInstance = ieBonusRules.getConstructor(String.class).newInstance("IE");
BonusRules rules = (BonusRules) ieInstance;   // "they have the same name, this must work"
```

Measured output on JDK 21.0.7:

```
ClassCastException: class com.quizstakes.bonus.BonusRules cannot be cast to class
com.quizstakes.bonus.BonusRules (com.quizstakes.bonus.BonusRules is in unnamed module
of loader 'ie-ruleset' @33909752; com.quizstakes.bonus.BonusRules is in unnamed module
of loader 'app')
```

**Right**

```java
// Define the bridge type ONCE, in a common ancestor loader, and keep it off the child's path.
// Both children's implementations then implement the SAME interface class.
public interface BonusRuleSet {          // on the parent classpath only
    String jurisdiction();
    long grantCapMinorUnits();
}

BonusRuleSet rules = (BonusRuleSet) ieBonusRules.getConstructor(String.class).newInstance("IE");
System.out.println(rules.grantCapMinorUnits());
```

The cast succeeds because `BonusRuleSet` has exactly one defining loader — the parent's — so there is only one `<com.quizstakes.bonus.BonusRuleSet, app>` in the JVM for both children to implement.

**Why people believe it:** every other part of Java treats the fully-qualified name as the type's identity — imports, `Class.getName()`, stack traces, `equals` on `String` names — so the loader half of the pair is invisible until it bites, and on Java 8 the message did not mention loaders at all.

### Drawing the loader hierarchy with an extension loader

**Wrong**

```java
// Belief: bootstrap -> extension -> application, and extensions live in $JAVA_HOME/lib/ext.
ClassLoader extensions = ClassLoader.getSystemClassLoader().getParent();
System.out.println(extensions.getName());   // "surely ext"
```

Measured on JDK 21.0.7 the parent's name is `platform`, not `ext`, and the mechanism the belief rests on is refused at launch:

```
$ java -Djava.ext.dirs=/tmp -version
-Djava.ext.dirs=/tmp is not supported.  Use -classpath instead.
Error: Could not create the Java Virtual Machine.
```

**Right**

```java
ClassLoader application = ClassLoader.getSystemClassLoader();   // name "app"
ClassLoader platform = ClassLoader.getPlatformClassLoader();    // name "platform"
System.out.println(application.getParent() == platform);        // true
System.out.println(platform.getParent());                       // null -- that IS bootstrap
```

**Why people believe it:** the extension loader was correct for every Java version from 1.2 to 8, and JEP 220 removed it in Java 9. Diagrams outlive releases, and the extension loader is still the most commonly drawn three-box picture on the internet.

### Catching `ClassNotFoundException` to handle a class that fails as `NoClassDefFoundError`

**Wrong**

```java
public long grantCapMinorUnits() {
    try {
        BonusRules rules = new BonusRules();   // compiled-in symbolic reference
        return rules.grantCapMinorUnits();
    } catch (ClassNotFoundException e) {       // does not compile: nothing here throws it
        return 0L;
    }
}
```

Written the way it actually appears in the field — the `catch` around a reflective call, and the direct reference a few lines down — the `Error` walks straight past it:

```
Exception in thread "main" java.lang.NoClassDefFoundError: BonusRules
	at BonusService.main(BonusService.java:14)
Caused by: java.lang.ClassNotFoundException: BonusRules
```

**Right**

```java
// An optional dependency must be reached ONLY reflectively, behind an interface you own,
// so that javac never emits a constant-pool reference to the optional class.
public long grantCapMinorUnits(String adapterBinaryName, ClassLoader loader) {
    try {
        Class<?> adapterClass = Class.forName(adapterBinaryName, true, loader);
        BonusRuleSet adapter = (BonusRuleSet) adapterClass.getConstructor().newInstance();
        return adapter.grantCapMinorUnits();
    } catch (ClassNotFoundException e) {
        return 10_000L;   // documented default: grant cap of 100 in minor units
    } catch (ReflectiveOperationException e) {
        throw new IllegalStateException("rule-set adapter not constructible: " + adapterBinaryName, e);
    }
}
```

**Why people believe it:** the two failures print the same missing class name, and the `NoClassDefFoundError`'s `Caused by:` really *is* a `ClassNotFoundException` — so the log looks like the exception the `catch` names, even though the thing propagating is an `Error` from a different code path.

### Reaching for double-checked locking when the holder idiom is available

**Wrong**

```java
private static FundsLedger instance;          // no volatile
public static FundsLedger instance() {
    if (instance == null) {
        synchronized (FundsLedger.class) {
            if (instance == null) {
                instance = new FundsLedger(Currency.getInstance("GBP"));
            }
        }
    }
    return instance;
}
```

Without `volatile` this is broken on every JDK: a `balance-view-4` thread may see a non-null `instance` whose `minorUnitsByPosition` map is still null, because nothing orders the constructor's writes before the publishing write. Adding `volatile` makes it correct, and it is still 21 bytecode instructions with a `monitorenter`, a `monitorexit`, and a two-entry exception table — measured with `javap -c -p` on JDK 21.0.7.

**Right**

```java
private static final class Holder {
    static final FundsLedger INSTANCE = new FundsLedger(Currency.getInstance("GBP"));
}
public static FundsLedger instance() {
    return Holder.INSTANCE;                   // getstatic; areturn -- 2 instructions
}
```

Correct by JVMS §5.5's exactly-once initialization, with the happens-before edge preserved even when the implementation elides the lock, and with nothing for a future maintainer to break by deleting a keyword.

**Why people believe it:** double-checked locking is the canonical textbook answer to lazy initialization and reads as the "advanced" choice, while the holder idiom looks like it must be hiding something because it contains no concurrency construct at all. The concurrency construct is in the VM.

## Cheat sheet

| Item | Value |
|---|---|
| Loader hierarchy on Java 21 | bootstrap → platform → application (system) |
| Bootstrap loader | Represented as `null`; not a Java object; `String.class.getClassLoader()` measured `null` |
| Platform loader | `ClassLoader.getPlatformClassLoader()`, `getName()` = `platform`, `getParent()` = `null` |
| Application loader | `ClassLoader.getSystemClassLoader()`, `getName()` = `app`, parent = platform |
| Extension loader | **Removed in Java 9** (JEP 220); `-Djava.ext.dirs` refused at launch on 21 |
| Delegation order (`loadClass(String, boolean)`) | `findLoadedClass` → parent `loadClass` (bootstrap if parent is `null`) → `findClass`; `resolveClass` only if `resolve` |
| Override point | `findClass`, per javadoc — override `loadClass` only to break parent-first deliberately |
| Class identity | The pair `<N, L_d>` — binary name plus **defining** loader (JVMS 21 §5.3) |
| Initiating vs defining loader | Initiating = asked; defining = called `defineClass`. `Class.getClassLoader()` returns the **defining** loader |
| Loading constraints | JVMS 21 §5.3.4 — `N^L1 = N^L2` imposed at preparation and resolution; violation is a `LinkageError` |
| Two-loader symptom | `ClassCastException` naming the same class twice, disambiguated by `(… loader 'ie-ruleset' …; … loader 'app')` |
| Two-loader fix | Shared interface defined once by a common ancestor loader; never cast between children |
| Loader GC unit | Loader + every class it defined + their statics; one leaked reference pins the set `[X-REF 06]` |
| `ClassNotFoundException` | `ReflectiveOperationException` → `Exception` (checked); thrown by `Class.forName`/`loadClass` |
| `NoClassDefFoundError` (linkage) | `LinkageError` → `Error`; JVM resolving a constant-pool reference; `Caused by: ClassNotFoundException` |
| `NoClassDefFoundError` (failed init) | `LinkageError` → `Error`; class present, `<clinit>` already threw; owned by `03a` |
| JVMS §5.3.1 wrapping | "loading and creating C then fails with a `NoClassDefFoundError` whose cause is the `ClassNotFoundException`" |
| JDK-8048190 | Failed-init `NoClassDefFoundError` gained a reconstructed `Caused by:` — fixed JDK 18, backported 17.0.7 / 11.0.19 / 8u341 |
| `Class.forName(String)` | Initializes; `ClassNotFoundException`; caller's own loader |
| `Class.forName(String, boolean, ClassLoader)` | Initializes only if `initialize` is true; `ClassNotFoundException`; the loader you pass (`null` = bootstrap) |
| `ClassLoader.loadClass(String)` | Equivalent to `loadClass(name, false)` — no resolution, no initialization |
| `Class.forName(Module, String)` | Java 9+; does not link, does not initialize; returns **`null`** on failure, not an exception |
| Context class loader | `Thread.get/setContextClassLoader`; lets parent-defined framework code reach child-visible types |
| `ServiceLoader.load(Class)` | Uses the current thread's context class loader; `load(Class, ClassLoader)` does not |
| Holder idiom steady-state bytecode | `0: getstatic; 3: areturn` — measured with `javap -c -p` on JDK 21.0.7 |
| Alternatives, measured instruction counts | eager 2 · holder 2 · `synchronized` 8 + monitor · DCL 21 + monitorenter/exit + exception table · enum 2 |
| Exactly-once guarantee | JVMS §5.5: "If the `Class` object for C indicates that C has already been initialized, then no further action is required." |
| Lock-elision permission | JVMS §5.5: implementation **may** elide the lock "provided that […] all happens-before orderings […] still exist" |
| DCL version trap | Broken before Java 5 (pre-JSR-133 memory model); still broken today without `volatile` |
| Holder idiom's limit | Static singletons only — a generic/instance-level lazy field cannot use the class-init lock |
| CDS flags verified on 21.0.7 | `-Xshare:auto|off|on`; `-XX:SharedArchiveFile`, `-XX:ArchiveClassesAtExit`, `-XX:DumpLoadedClassList`, `-XX:SharedClassListFile`, `-XX:ExtraSharedClassListFile`, `-XX:AutoCreateSharedArchive` |
| Default CDS archive on 21.0.7 | `lib/server/classes.jsa`, 14,647,296 bytes; mapped by default (`-Xlog:cds=info`) |
| Measured class load, trivial program | 627 classes, 604 of them from the shared archive (JDK 21.0.7) |
| CDS caches | Loaded-and-linked form, not initialization — `FundsLedger$Holder` still loaded lazily from the archive |
| JEP 483 | "Ahead-of-Time Class Loading & Linking", Closed/Delivered, **Release 24**, issue 8315737 |
| JEP 483 figures (attributed) | HelloStream 0.031s → 0.018s; PetClinic 3.2.0 4.486s → 2.604s; both 42%; caches 11.4 MB / 130 MB |
| JEP 483 non-goal | Does not cache classes loaded by user-defined class loaders |
| Lazy-constant chain | Draft **8209964** "Lazy Static Final Fields" (Draft, John Rose) → **JEP 502** Stable Values, JDK 25 → **JEP 526** Lazy Constants (2nd Preview), JDK 26 → **JEP 531** Lazy Constants (3rd Preview), JDK 27 |
| On Java 21 | None of the lazy-constant API exists; the holder idiom is the whole toolkit |

## Self-test

**Q1.** A `ClassCastException` says `class com.quizstakes.bonus.BonusRules cannot be cast to class com.quizstakes.bonus.BonusRules`. Explain the mechanism, and say what you would change.

<details><summary>Answer</summary>

A run-time class is identified by the pair of its binary name and its **defining** loader — JVMS 21 §5.3 writes it as `<N, L_d>`. Two loaders that each define the same bytes therefore produce two distinct `Class` objects with equal names, and the type system treats them as unrelated: measured on JDK 21.0.7, `==` is false and `isAssignableFrom` is false in both directions. The parenthetical clause in the message is the diagnostic — on JDK 21 it names each side's module and loader, for example `loader 'ie-ruleset'` versus `loader 'app'`. On Java 8 that clause was absent, which is why the failure has a reputation for being unexplainable.

The three common causes: the same jar on both the parent and child classpath; a hot redeploy that left the old loader alive; an application server splitting shared and per-application classpaths. The fix is never to cast. Define the bridge type — an interface such as `BonusRuleSet` — exactly once, in a common ancestor loader, and keep it off the children's paths, so both children's implementations implement the same interface class. Then pass values across as that interface.

</details>

**Q2.** Name the three loaders on Java 21, their accessors, and the one that people usually get wrong.

<details><summary>Answer</summary>

Bootstrap, platform, application. Bootstrap has no accessor because it is not a Java object — it is represented as `null`, which is why `String.class.getClassLoader()` returns `null` and why null-checking loader references is mandatory. Platform is `ClassLoader.getPlatformClassLoader()`, `getName()` measured `platform`, and its `getParent()` is `null` (that *is* bootstrap). Application, also called system, is `ClassLoader.getSystemClassLoader()`, `getName()` measured `app`, parent platform.

The one people get wrong is the second: there is no extension class loader. JEP 220, Release 9, removed the extension mechanism along with `java.ext.dirs`, and the platform loader took its structural position. On JDK 21.0.7, `java -Djava.ext.dirs=/tmp -version` refuses to start with `-Djava.ext.dirs=/tmp is not supported.  Use -classpath instead.` Every pre-9 diagram still shows bootstrap/extension/application; that picture has been wrong for four LTS releases.

</details>

**Q3.** Walk the default `loadClass` algorithm and say what each of its three steps buys you.

<details><summary>Answer</summary>

Per the Java 21 javadoc for `ClassLoader.loadClass(String, boolean)`: (1) invoke `findLoadedClass` to check whether the class has already been loaded; (2) invoke `loadClass` on the parent, or the VM's built-in loader if the parent is `null`; (3) invoke `findClass`. If found and `resolve` is true, then `resolveClass`.

Step 1 makes loading idempotent per loader — a second request for the same name returns the same `Class` object, which is why one loader can never define one name twice. Step 2 is the parent-first rule, and it is what makes the platform's own types unforgeable: a name the parent can supply is always answered by the parent, so `java.lang.String` is defined exactly once no matter what is on your classpath. The `null` clause is how a loader constructed with a `null` parent reaches bootstrap directly, skipping platform and application. Step 3 is the only step that actually **defines** a class, and it is the step the javadoc tells you to override. Overriding `loadClass` itself is how you deliberately break the ordering — child-first, for a plugin loader — and that is exactly what creates the two-loader identity situation.

</details>

**Q4.** Distinguish `ClassNotFoundException` from `NoClassDefFoundError`, then say why there are actually three cases.

<details><summary>Answer</summary>

`ClassNotFoundException` is a checked exception — `ReflectiveOperationException` under `Exception` — thrown by an explicit lookup you wrote, `Class.forName` or `ClassLoader.loadClass`. It is a legitimate answer to a question, which is why it is checked. `NoClassDefFoundError` is a `LinkageError` under `Error`, thrown by the JVM.

The third case is what completes the answer. Case two is a **linkage** failure: the class was on the compile classpath, `javac` emitted a symbolic reference into the constant pool, and the class is absent at run time. JVMS §5.3.1 says the loader's `ClassNotFoundException` gets wrapped: "The process of loading and creating C then fails with a `NoClassDefFoundError` whose cause is the `ClassNotFoundException`." Measured on JDK 21.0.7, the stack really does show that nesting, with the cause's frames inside `BuiltinClassLoader.loadClass`. Case three is a **failed initialization**: the class is present and linked, but its `<clinit>` already threw, so every subsequent use gets a `NoClassDefFoundError` for a class that is physically there. The field tell between two and three is the cause: a `ClassNotFoundException` in the loader's frames means a deployment problem; anything else means hunt for the original `ExceptionInInitializerError`. On JDK 21 case three does carry a reconstructed `Caused by:` — JDK-8048190, fixed in 18 and backported to 17.0.7, 11.0.19 and 8u341 — so the pre-fix folklore that it is untraceable is stale.

</details>

**Q5.** Prove that the holder-class idiom is the *cheapest correct* lazy singleton, rather than just asserting it.

<details><summary>Answer</summary>

Correctness first, from JVMS 21 §5.5: "If the `Class` object for C indicates that C has already been initialized, then no further action is required. Release LC and complete normally." That is exactly-once per class per loader, under a per-class lock, with all other threads blocking until it completes — so `Holder.INSTANCE` is assigned once and every later reader sees the fully constructed object. No double-checked locking is needed because the VM already does check-lock-check-initialize on your behalf.

Cheapness from the immediately following permission: the implementation "may optimize this procedure by eliding the lock acquisition […] provided that, in terms of the Java memory model, all happens-before orderings […] that would exist if the lock were acquired, still exist when the optimization is performed." That is a permission granted to the implementation, not observed HotSpot behaviour, and the proviso is what makes it safe — the ordering survives the elision. So correctness comes from the initialization guarantee and the steady-state cost may legally fall to a bare field read.

Then the measurement, `javap -c -p` on JDK 21.0.7: the accessor is `0: getstatic; 3: areturn` — two instructions, no null check, no monitor. The `synchronized` accessor measured eight instructions plus an `ACC_SYNCHRONIZED` monitor on every entry and exit. Double-checked locking with `volatile` measured twenty-one instructions with `monitorenter`/`monitorexit` and a two-entry exception table. And laziness is measured too: under `-Xlog:class+load=info`, `FundsLedger` loaded when its class literal was evaluated and `FundsLedger$Holder` only three milliseconds later, at the `instance()` call. The holder idiom ties the cheapest option in the table while being the only lazy one that requires no memory-model reasoning from the author.

</details>

**Q6.** When would you use `Class.forName(name, false, loader)` rather than `Class.forName(name)`, and what does the loader argument actually decide?

<details><summary>Answer</summary>

The one-argument form does two things you may not want: it initializes the class — the javadoc says "A call to `forName("X")` causes the class named `X` to be initialized" — and it uses the caller's own defining loader. Pass `initialize=false` when you want to inspect a class reflectively without running arbitrary code in its `<clinit>`; that matters for plugin scanning, where triggering initialization means executing a third party's static block during discovery.

The loader argument decides the class's **identity**. `Class.forName` initiates loading through the loader you pass, so the resulting class is `<name, whichever loader ultimately defined it>` after delegation — possibly the loader you passed, possibly one of its ancestors. Pass the wrong loader and you get a `Class` object that is name-identical to, and type-incompatible with, the one the rest of your code compiled against, and the failure surfaces later as the same-name `ClassCastException`. `null` for the loader means bootstrap. Worth also knowing the fourth family member: `Class.forName(Module, String)`, added in Java 9, neither links nor initializes and reports failure by returning `null` rather than throwing — so a null check replaces the `catch` there.

</details>

**Q7.** A Spring service reads a JDBC driver name from configuration and cannot find it, even though the driver jar is on the classpath. Where does the context class loader come into it?

<details><summary>Answer</summary>

Parent-first delegation has a structural hole: a class defined by a parent loader can never see a class visible only to a child. `java.sql.DriverManager` is defined by the platform loader; the driver sits on the application classpath, which the platform loader cannot see by construction. `Thread.getContextClassLoader()`/`setContextClassLoader()` is the escape hatch — a mutable per-thread loader reference that framework code consults instead of its own `getClass().getClassLoader()`, letting parent-defined code reach downward. The same hole is why `ServiceLoader.load(Class)` uses it: the Java 21 javadoc says it is "equivalent to `ServiceLoader.load(service, Thread.currentThread().getContextClassLoader())`". JPA provider discovery and Spring's `ClassUtils` sit in the same place.

The failure mode when this is used wrongly is worth naming. The context class loader is a mutable field on a `Thread`, not a scoped construct, and QuizStakes runs its request path on pooled threads such as `http-nio-8443-exec-7`. Set it without restoring it in a `finally` and the next unrelated task inherits a loader that may already be closed — a `ClassNotFoundException` in code that never mentions class loading — or the discarded loader is pinned in metaspace for the life of the pool thread, which is the leak the `ServiceLoader` javadoc explicitly warns about. Where you know which loader you mean, prefer the two-argument `ServiceLoader.load(Class, ClassLoader)`, which does not consult the context loader at all.

</details>

**Q8.** Why is application startup time a capacity concern for a service like QuizStakes, and what does JDK 21 already give you about it?

<details><summary>Answer</summary>

Because every instance added under load pays the full class-loading-and-initialization bill before serving its first request. QuizStakes runs 14k concurrent sessions steady and 55k at peak, and registrations swing from 12k to 40k a day; absorbing a near-4x swing means scaling out *during* the peak, so a startup measured in seconds puts the autoscaler structurally behind the traffic. The bill is not small: measured on JDK 21.0.7, a program that only prints its loaders already loaded 627 classes, and JEP 483 reports that Spring PetClinic 3.2.0 "loads and links about 21,000 classes at startup." There is no measured QuizStakes figure — what you would measure is `-Xlog:class+load=info` for count and timing, `-Xlog:class+init`, and a JFR startup profile.

What 21 gives you is CDS and AppCDS. A default archive ships with the JDK — `lib/server/classes.jsa`, 14,647,296 bytes on this install — and is mapped by default, which is why 604 of those 627 classes came from the shared archive rather than from disk. For application classes, the verified round trip on 21.0.7 is `-XX:ArchiveClassesAtExit=qs.jsa` to dump and `-XX:SharedArchiveFile=qs.jsa` to consume, after which application classes log `source: shared objects file (top)`. The cost is a training run and an archive file to version alongside the artefact. What arrives later is JEP 483, "Ahead-of-Time Class Loading & Linking", Release **24**, which caches the loaded-and-linked form and reports 42% startup improvements on both a short Stream program (0.031s → 0.018s) and PetClinic (4.486s → 2.604s), with 11.4 MB and 130 MB caches respectively — and explicitly does not cache classes from user-defined loaders.

</details>

**Q9.** The syllabus calls 3.6.16 "the JEP draft for lazy static final fields." What is actually the state of play, and why does it matter on Java 21?

<details><summary>Answer</summary>

The phrasing is stale — there is a draft, but the work that shipped took a library route instead. The draft is JEP draft **8209964, "Lazy Static Final Fields"**, owner John Rose, Status Draft, created 2018 and last updated 2023, never promoted to a mainline number. It states the problem precisely: class initializers are coarse-grained, their contract is to run *all* of a class's initialization rather than the part pertaining to one field, and "it only takes one extra-complicated static field in a class to make all fields non-optimizable."

What actually shipped is a preview API, three times: **JEP 502, "Stable Values (Preview)"** in JDK 25; **JEP 526, "Lazy Constants (Second Preview)"** in JDK 26, which renamed `StableValue` to `LazyConstant`; and **JEP 531, "Lazy Constants (Third Preview)"** in JDK 27, which adds `Set.ofLazy`. Both 526 and 531 list as an explicit non-goal "to enhance the Java programming language with a means to declare lazy fields," so the draft's language route is for now abandoned.

Why it matters on 21: none of it exists there. The draft itself names the internal mechanism — `@Stable`, "an increasingly important part of JDK internals" since Java 7 — and the connection worth making is that `@Stable` is the JDK-internal mechanism this line of work exposes safely to application code; `@Stable` and JIT constant folding are `04-internals-final-and-constant-folding.md`. On Java 21 the holder-class idiom is the whole toolkit, and its cost is exactly what the draft describes as the workaround's price: one extra class per lazily-initialised constant.

</details>

## Open questions

- Whether JEP 483's ahead-of-time cache stores any *initialization* state. The JEP's Description names only reading, parsing, loading and linking as shifted ahead of time, and its Motivation lists static-initializer execution as a separate third activity, but the JEP body does not state either way whether `<clinit>` results are cached. Settled by the AOT-cache implementation notes or by measuring `-Xlog:class+init` against an AOT cache on JDK 24 or later, which this machine cannot do (JDK 21.0.7 and GraalVM 25.0.1 are the JDKs present, and 25's `-XX:AOT*` behaviour is out of this file's scope).
- The `@33909752` suffix in the measured `ClassCastException` loader clause is an identity-hash-derived label and will differ per run; the loader *name* (`ie-ruleset`) is the stable part. Verified as reproducible in shape but not in value.

---

**Leaves covered:** 3.6.11, 3.6.12, 3.6.13, 3.6.14, 3.6.15, 3.6.16, 3.6.17 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 833
