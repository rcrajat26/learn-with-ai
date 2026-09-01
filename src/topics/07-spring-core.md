# 07 — Spring Core

The container, the proxy model, and Boot's auto-configuration. Most Spring bugs that reach production
are not "Spring is confusing" — they are one of three mechanisms misunderstood: *what a bean actually
is*, *that your bean is not your class but a proxy wrapping it*, and *when the transaction actually
commits*. This guide is built around those three.

---

## 1. Inversion of Control and the ApplicationContext

**Mechanism.** You do not call `new`. At startup Spring scans for bean definitions (annotated classes,
`@Bean` methods, imported configurations), builds a `BeanDefinition` registry — a map of name →
metadata (class, scope, dependencies, init/destroy methods) — then instantiates and wires them.
The `ApplicationContext` *is* that registry plus the instantiated singletons. Two phases matter:
**definition registration**, where nothing is instantiated yet and `BeanFactoryPostProcessor`s can
still mutate definitions (how `@ConfigurationProperties` binding and placeholder resolution hook in),
then **instantiation and wiring**, where singletons are created eagerly, dependencies resolved,
`BeanPostProcessor`s run, and proxies created.

**Why IoC at all:** the object graph is described declaratively in one place, so swapping an
implementation (real payment gateway → stub) is a configuration change, not an edit across call sites.
That is also exactly what makes the code testable — see `16-testing.md`.

---

## 2. Dependency injection: constructor vs field vs setter

```java
@Service
public class OrderService {
    private final PaymentClient payments;
    // No @Autowired needed since Spring 4.3 for a single constructor.
    public OrderService(PaymentClient payments) { this.payments = payments; }
}
```

**Constructor injection is the answer, and here is the actual reasoning — four independent arguments:**

1. **Immutability.** Fields can be `final`. A field-injected dependency can never be `final`, because
   Spring sets it by reflection *after* construction.
2. **No half-built object.** With constructor injection the object is either fully valid or was never
   created. Field injection means a window where the object exists with `null` collaborators.
3. **Testability without a container.** `new OrderService(mockPayments, mockOrders)` just works.
   Field injection forces reflection (`ReflectionTestUtils`) or a Spring context in unit tests.
4. **Design pressure.** A constructor with eight parameters is visibly ugly, which surfaces the
   SRP violation. Eight `@Autowired` fields look tidy and hide it.

**Mechanism of field injection:** Spring instantiates via the no-arg constructor, then
`AutowiredAnnotationBeanPostProcessor` walks the fields with reflection and calls
`Field.setAccessible(true)` before assigning.

**Trap:** "Field injection is fine, Spring handles it." The failure is not at runtime in Spring — it's
in tests and in circular-dependency masking (§ 18). Field injection *hides* cycles that constructor
injection would fail loudly on at startup.

**Resolution rules when multiple candidates exist**, in order: `@Qualifier("name")` → `@Primary` →
parameter name matching the bean name → `NoUniqueBeanDefinitionException`.

Injecting a `List<Validator>` or `Map<String, Validator>` gives you all beans of that type — the
canonical way to implement a strategy/plugin set. `@Order` controls list order.

---

## 3. Stereotypes

| Annotation | Meaning | Extra behaviour |
|---|---|---|
| `@Component` | Generic managed bean | none |
| `@Service` | Business logic | none technically — semantic marker |
| `@Repository` | Data access | **exception translation** |
| `@Controller` / `@RestController` | Web layer | MVC handler mapping |
| `@Configuration` | Bean definitions | CGLIB-proxied (§ 5) |

**`@Repository` is the only one with real mechanics.** `PersistenceExceptionTranslationPostProcessor`
wraps `@Repository` beans in a proxy that catches vendor-specific exceptions (Hibernate's
`ConstraintViolationException`, a raw `SQLException` with a vendor code) and rethrows them as
Spring's `DataAccessException` hierarchy — `DataIntegrityViolationException`,
`DuplicateKeyException`, `OptimisticLockingFailureException`. That's what keeps your service layer
from importing `org.hibernate`.

**Trap:** believing `@Service` does something special. It doesn't. If you swap `@Service` for
`@Component` nothing changes. If you swap `@Repository` for `@Component` you lose exception
translation. Say that in an interview and you're visibly a level above.

---

## 4. Scopes and the singleton-statefulness trap

- `singleton` (default) — **one instance per container**, not per JVM, not per classloader.
- `prototype` — new instance per injection/lookup. Spring does **not** manage its destruction;
  `@PreDestroy` is never called on a prototype.
- `request`, `session`, `application` — web-aware scopes.

**The trap that fails candidates:** a singleton with mutable instance state is shared across every
concurrent request thread.

```java
@Service
public class ReportService {
    private List<Row> buffer = new ArrayList<>();   // BUG: shared across all request threads
    public Report build(Query q) {
        buffer.clear();               // another request is mid-addAll right now
        buffer.addAll(query(q));
        return summarize(buffer);
    }
}
```

Fix: make it a local variable. Beans should be stateless; state lives in method locals or in a
request-scoped holder. See `05-multithreading-concurrency.md` for why "it worked in testing" —
single-threaded tests never expose it.

**Injecting a prototype into a singleton** gives you *one* prototype instance, captured at wiring
time — the singleton is only wired once. Fixes: inject `ObjectProvider<T>` and call `getObject()`
per use, or use `@Lookup`, or scoped-proxy (`@Scope(value="prototype", proxyMode=TARGET_CLASS)`).
The same trick is what makes request-scoped beans injectable into singletons: you get a proxy that
resolves the real instance per request from the thread-bound context.

---

## 5. The proxy model — the single most important Spring mechanism

Everything declarative — `@Transactional`, `@Cacheable`, `@Async`, `@Retryable`, `@PreAuthorize` —
works the same way: **your bean in the context is not your object. It is a proxy that wraps your
object and runs interceptors around the method call.**

```
caller ──▶ [ Proxy ] ──▶ interceptor chain (tx, cache, security) ──▶ your real instance
```

### JDK dynamic proxy vs CGLIB

| | JDK dynamic proxy | CGLIB |
|---|---|---|
| Requires | target implements an interface | nothing |
| Produces | a class implementing the same interfaces | a **subclass** of your class |
| Injectable as | the interface only | the class or interface |
| Can't advise | non-interface methods | `final` classes, `final`/`private`/`static` methods |

Spring Boot defaults to **CGLIB for everything** (`spring.aop.proxy-target-class=true`) precisely so
that injecting by concrete class works. Plain Spring historically used JDK proxies when an interface
was present.

**CGLIB mechanics:** the generated subclass overrides each non-final public/protected method and
delegates to the interceptor chain. So a `final` class cannot be proxied at all; a `final`, `private`,
or `static` method cannot be overridden, meaning **an annotation on it is silently ignored**; the
constructor effectively runs twice (proxy subclass + target), so never put side effects there; and
fields on the proxy instance are not the target's fields, so never read state off the proxy.

**Trap:** `@Transactional private void save()` compiles and does absolutely nothing. There's no error.

### Self-invocation — the bypass

```java
@Service
public class InvoiceService {
    public void processAll(List<Invoice> list) {
        list.forEach(this::processOne);      // `this` = the RAW object, not the proxy
    }

    @Transactional
    public void processOne(Invoice i) { ... } // NOT transactional when called above
}
```

The proxy only intercepts calls that come *in through it*. `this.processOne(...)` is a plain virtual
call inside the target; the interceptor chain is never entered. Same for `@Cacheable` (cache never
consulted) and `@Async` (runs synchronously on the caller thread).

**Ranked fixes:** (1) move the annotated method to a **different bean** and inject it — cleanest, makes
the boundary a visible collaboration; (2) self-inject the proxy, `@Autowired @Lazy private InvoiceService
self;` (the `@Lazy` breaks the cycle) — works, but a smell; (3) `AopContext.currentProxy()` with
`exposeProxy = true`, which ties code to Spring; (4) programmatic `TransactionTemplate`, best when you
want fine-grained boundaries anyway; (5) AspectJ weaving — a real fix, rarely worth the build complexity.

**How to spot it in review:** any `this.someAnnotatedMethod()` — or a private helper carrying
`@Transactional`/`@Async`/`@Cacheable`.

### `@Configuration` proxying

`@Configuration` classes are CGLIB-proxied too, so calling one `@Bean` method from another returns
the *singleton*, not a new object. With `@Configuration(proxyBeanMethods = false)` (the "lite" mode
Boot's own auto-config uses for startup speed) that guarantee is gone — an inter-method call creates
a fresh instance.

---

## 6. Bean lifecycle

Order for a singleton: constructor (constructor injection) → field/setter injection → `*Aware`
callbacks → `BeanPostProcessor.postProcessBeforeInitialization` → `@PostConstruct` →
`InitializingBean.afterPropertiesSet()` → custom `initMethod` →
**`BeanPostProcessor.postProcessAfterInitialization`, where AOP proxies are created** → bean in use →
`@PreDestroy` → `DisposableBean.destroy()` → custom `destroyMethod` (singletons only, on context close).

Two things fall out of the proxy-creation step:
- **Calling a `@Transactional` method from your own `@PostConstruct` is not transactional** — the
  proxy doesn't exist yet at that point, and you're on the raw instance regardless.
- `BeanPostProcessor` beans themselves are created very early and cannot be advised.

`ApplicationRunner` / `CommandLineRunner` run *after* the context is fully refreshed — that's the
right place for startup work that needs transactions or proxies.

---

## 7. `@Transactional` in depth

**Mechanism.** The interceptor gets a `Connection`, calls `setAutoCommit(false)`, binds it to the
thread via `TransactionSynchronizationManager` (a `ThreadLocal`), calls your method, then commits or
rolls back and unbinds. Every JDBC/JPA operation on that thread picks up the bound connection — that's
how "the transaction" is ambient.

### Propagation

| Propagation | Existing tx | No tx |
|---|---|---|
| `REQUIRED` (default) | join it | start one |
| `REQUIRES_NEW` | **suspend** it, start an independent one | start one |
| `SUPPORTS` | join | run non-transactionally |
| `NOT_SUPPORTED` | suspend, run without | run without |
| `MANDATORY` | join | **throw** |
| `NEVER` | **throw** | run without |
| `NESTED` | JDBC savepoint inside the outer tx | start one |

`REQUIRES_NEW` is the tool for "write the audit row even if the business tx rolls back" — it uses a
**second connection**, so it can deadlock against the suspended one if both touch the same rows, and it
doubles pool usage (Hikari sizing in `09-sql-databases.md`). `NESTED` rolls back to a savepoint so the
outer transaction survives; `REQUIRES_NEW` commits independently and the outer rollback cannot undo it.

### Rollback rules — the classic trap

**By default Spring rolls back on `RuntimeException` and `Error`, and *commits* on checked exceptions.**

```java
@Transactional                      // commits despite the exception!
public void transfer() throws InsufficientFundsException { ... }

@Transactional(rollbackFor = Exception.class)   // fix
```

**Trap:** catching an exception inside a `REQUIRED` inner method and swallowing it. The inner
interceptor already marked the shared transaction rollback-only, so the outer commit throws
`UnexpectedRollbackException` — "Transaction silently rolled back because it has been marked as
rollback-only". The message is confusing; the cause is always this.

### `readOnly = true` and other attributes

Not just a hint: sets the JDBC connection read-only (the driver may refuse writes), and — the part
that matters — puts Hibernate's flush mode to `MANUAL`, so **dirty checking is skipped**. That is a
real performance win on read paths and a real surprise if you expected an update to persist.

`timeout` is in seconds, enforced by the tx manager and propagated to statement timeouts where
supported. `isolation` maps to the JDBC isolation level — see `09-sql-databases.md` for the anomalies.
Place the annotation on the **service** layer, not the repository (`08-spring-data-jpa.md`), and on the
class or method rather than an interface method, which only works with JDK proxies.

---

## 8. Spring Boot auto-configuration mechanics

`@SpringBootApplication` = `@Configuration` + `@ComponentScan` + `@EnableAutoConfiguration`. The last
imports `AutoConfigurationImportSelector`, which reads every jar's
`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (pre-2.7: the
`spring.factories` file) — a plain list of configuration class names. Each candidate is filtered by its
`@Conditional` annotations, and survivors are registered **after** your own configuration, which is why
user-defined beans win.

Key conditions:

| Condition | Fires when |
|---|---|
| `@ConditionalOnClass` | class is on the classpath (that's why a starter jar "turns on" a feature) |
| `@ConditionalOnMissingBean` | you haven't defined one — **the back-off mechanism** |
| `@ConditionalOnProperty` | property present/equal to a value |
| `@ConditionalOnBean` | some other bean exists (order-sensitive; use with care) |
| `@ConditionalOnWebApplication` | servlet/reactive context |

**A "starter" is a dependency aggregator**: `spring-boot-starter-web` contains almost no code, just
the POM pulling in Spring MVC, Jackson, and embedded Tomcat. The auto-config lives in
`spring-boot-autoconfigure`, gated on those classes appearing.

**Diagnosing:** run with `--debug` (or `-Ddebug`) for the **conditions evaluation report** — every
auto-configuration listed as "Positive matches" / "Negative matches (reason)". This is the single
best answer to "why isn't my DataSource being created" / "why is one being created". Exclude with
`@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)`.

---

## 9. Configuration and profiles

`@Value("${app.timeout:30}")` injects one property with a default. `@ConfigurationProperties` binds
a whole prefix to a typed object:

```java
@ConfigurationProperties(prefix = "app.payment")
@Validated
public record PaymentProps(@NotBlank String apiUrl, @Positive Duration timeout, int retries) {}
```

**Prefer `@ConfigurationProperties`:** type safety, relaxed binding (`api-url`, `API_URL`,
`apiUrl` all bind), JSR-303 validation at startup instead of a `NumberFormatException` at 3am, IDE
autocomplete via the metadata processor, and grouping that documents itself.

**Property precedence** (later wins, abbreviated): defaults in code → `application.yml` in jar →
profile-specific `application-{profile}.yml` → OS environment variables → JVM system properties →
command-line args. Environment variables beating the yml file is how containers configure apps —
and how a stale env var overrides the config you just edited.

Profiles: `@Profile("!prod")` on beans, `spring.profiles.active`. **Trap:** using profiles to hold
secrets or environment URLs in git. Config belongs in the environment; profiles select *behaviour*
(e.g. an in-memory stub vs a real client), not credentials. See `13-web-security.md`.

---

## 10. Spring MVC request flow

```
request → Filter chain → DispatcherServlet
  → HandlerMapping picks handler + interceptor chain
  → HandlerInterceptor.preHandle
  → HandlerAdapter invokes controller
      argument resolvers (@RequestBody via HttpMessageConverter, @PathVariable, @RequestParam, ...)
  → return value handler (@ResponseBody → HttpMessageConverter → JSON)
  → postHandle → view render (if any) → afterCompletion
  → back out through the filter chain
```

`@RestController` = `@Controller` + `@ResponseBody` on every method: return values are serialized by
Jackson rather than resolved as a view name.

**Trap:** returning a JPA entity straight from a controller. It couples your API contract to the
schema, can trigger lazy loads during serialization (`LazyInitializationException` mid-response,
after the status line is already flushed), and leaks fields. Return a DTO/record.

### Exception handling

```java
@RestControllerAdvice
class ApiExceptionHandler {
    @ExceptionHandler(NotFoundException.class)
    ProblemDetail notFound(NotFoundException e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
    }
}
```

`@ControllerAdvice` is global; a `@ExceptionHandler` inside a controller takes precedence for that
controller. Most-specific exception type wins. `ProblemDetail` is Spring 6's RFC 7807 support — see
`12-api-design.md` for the contract shape.

### Validation

`@Valid @RequestBody CreateOrder body` triggers Bean Validation and throws
`MethodArgumentNotValidException` (→ 400) on failure. On a `@Validated` service class, constraint
violations on parameters throw `ConstraintViolationException` instead — a different exception,
easy to miss in the advice. Validation on a nested object requires `@Valid` on the field.

---

## 11. Events

```java
publisher.publishEvent(new OrderPlaced(orderId));

@EventListener                                     // synchronous, same thread, same transaction
@TransactionalEventListener(phase = AFTER_COMMIT)  // only after the tx actually commits
@Async @EventListener                              // other thread, NO transaction, NO caller context
```

- Plain `@EventListener` is **synchronous** — an exception in the listener propagates to the publisher
  and rolls the transaction back. People are consistently surprised by this.
- `@TransactionalEventListener(AFTER_COMMIT)` is the correct place to send an email / publish to Kafka:
  it guarantees you don't notify about an order that then rolled back. Note that by default a *new*
  database write inside an AFTER_COMMIT listener has no transaction — you need `REQUIRES_NEW`.
- `@Async` requires `@EnableAsync`, goes through the proxy (self-invocation bypass applies), and
  **swallows exceptions** unless the method returns `CompletableFuture` or you register an
  `AsyncUncaughtExceptionHandler`. The default executor in Boot 3 is a virtual-thread or
  `SimpleAsyncTaskExecutor`-based one — configure a real bounded pool; see
  `05-multithreading-concurrency.md`.
- `ThreadLocal`-bound context (security context, MDC, tx) does **not** cross into `@Async` unless you
  configure propagation (`DelegatingSecurityContextAsyncTaskExecutor`, MDC-copying decorator).

---

## 12. Filter vs Interceptor vs Aspect

| | Filter | HandlerInterceptor | AOP Aspect |
|---|---|---|---|
| Layer | Servlet container | Spring MVC | Any Spring bean |
| Sees | raw `HttpServletRequest`/`Response` | request + resolved handler + `ModelAndView` | method args + return value, typed |
| Can | wrap the stream, short-circuit before Spring | reject before controller, add model attrs | advise any bean method |
| Use for | CORS, security chain, request logging, MDC, gzip | auth checks needing handler metadata, timing per handler | transactions, caching, retry, custom cross-cutting logic |

Filters run outermost (`@Order` / `FilterRegistrationBean`), then interceptors, then aspects around the
controller method. Spring Security is a filter chain — which is why a security rejection never reaches
your `@ControllerAdvice` by default.

---

## 13. Scheduling

`@Scheduled(cron = "0 0 3 * * *", zone = "UTC")` — two traps, both common in production:

1. **The default scheduler has one thread.** Two `@Scheduled` methods, or one long-running job, and
   everything else queues behind it. Fix: define a `ThreadPoolTaskScheduler` bean or set
   `spring.task.scheduling.pool.size`.
2. **Every instance runs it.** Deploy three replicas and your nightly job runs three times.
   Fixes: ShedLock (a lock row in the DB), a leader-election flag, an external scheduler
   (Kubernetes CronJob, EventBridge) hitting one endpoint, or a queue with a single consumer.

`fixedDelay` measures from the *end* of the previous run; `fixedRate` from the *start* (so it can
overlap or pile up if a run exceeds the period).

---

## 14. Circular dependencies

Constructor A→B→A cannot be resolved — Spring throws `BeanCurrentlyInCreationException` at startup.
Field/setter injection *can* be resolved via the three-level singleton cache (an early reference is
exposed before initialization completes), which is exactly why field injection hides the design flaw.
Since Boot 2.6 circular references are **disabled by default**; `spring.main.allow-circular-references=true`
re-enables them and is a "we know it's broken" marker, not a fix. Real fixes, in order: extract the
shared logic into a third bean; invert with an event; if you truly must, `@Lazy` on one side (injects a
proxy, deferring resolution to first call).

---

## Atomic concept checklist

- [ ] I can describe the two container phases: bean-definition registration, then instantiation/wiring.
- [ ] I give four reasons for constructor injection — final fields, no half-built object, container-free tests, visible SRP pressure.
- [ ] I know field injection needs reflection and `setAccessible(true)`, and that it hides cycles.
- [ ] I know `@Repository` is the only stereotype with behaviour: exception translation to `DataAccessException`.
- [ ] I know singleton means one per container and that mutable instance state on a singleton is a data race.
- [ ] I know a prototype injected into a singleton is captured once; `ObjectProvider`/`@Lookup`/scoped proxy fix it.
- [ ] I can state the proxy model in one sentence: the context holds a proxy that runs interceptors before delegating to my object.
- [ ] I know Boot defaults to CGLIB subclass proxies, so `final`/`private`/`static` methods and `final` classes cannot be advised.
- [ ] I can explain self-invocation: `this.method()` skips the proxy, so `@Transactional`/`@Cacheable`/`@Async` silently do nothing.
- [ ] I can rank the self-invocation fixes: separate bean > self-injection with `@Lazy` > `AopContext` > `TransactionTemplate`.
- [ ] I know AOP proxies are created in `postProcessAfterInitialization`, so `@PostConstruct` is pre-proxy.
- [ ] I know the default rollback rule: runtime exceptions and errors roll back, **checked exceptions commit**; `rollbackFor` fixes it.
- [ ] I can explain `UnexpectedRollbackException` as an inner `REQUIRED` method marking the shared tx rollback-only.
- [ ] I know `REQUIRES_NEW` suspends and uses a second connection; `NESTED` uses a savepoint in the same one.
- [ ] I know `readOnly = true` sets Hibernate flush mode to MANUAL, disabling dirty checking.
- [ ] I can describe auto-configuration: `AutoConfiguration.imports` files filtered by `@Conditional`, user beans win via `@ConditionalOnMissingBean`.
- [ ] I know `--debug` prints the conditions evaluation report with positive/negative matches and reasons.
- [ ] I prefer `@ConfigurationProperties` over `@Value` for type safety, relaxed binding, and startup validation.
- [ ] I know environment variables outrank `application.yml` in the property precedence order.
- [ ] I can walk the DispatcherServlet flow: mapping → interceptors → adapter → argument resolvers → return-value handler → converters.
- [ ] I never return a JPA entity from a controller.
- [ ] I know `@EventListener` is synchronous and in-transaction; `@TransactionalEventListener(AFTER_COMMIT)` is the safe notify point.
- [ ] I know `@Async` swallows exceptions unless it returns a future, and does not propagate ThreadLocal context.
- [ ] I can place filter vs interceptor vs aspect by layer and by what each one can see.
- [ ] I know `@Scheduled` uses a single thread by default and runs on every replica.
- [ ] I know circular dependencies are disabled by default since Boot 2.6, and that field injection is what used to hide them.