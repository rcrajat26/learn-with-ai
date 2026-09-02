# Syllabus — 07 Spring Core

**Target version: Spring Framework 6.2.x / Spring Boot 3.5.x on Java 21 (Jakarta EE 10).**
Every class name, bean name, property key, default value and annotation attribute below is stated
against that baseline. Spring Framework 7.0 / Spring Boot 4.0 shipped in November 2025 and change
several things this topic teaches (Jackson 3, JSpecify null-safety, modularised autoconfigure jars,
built-in `@Retryable`/`@ConcurrencyLimit`, API versioning, `BeanRegistrar`, Jakarta EE 11); every
such divergence is marked `[VERSION-TRAP]` inline so the write pass states what is true in 6.2/3.5
and what changed after. The three deltas that most often produce a stale answer are
**`spring.factories` → `AutoConfiguration.imports` (Boot 2.7/3.0)**, **circular references disabled
by default (Boot 2.6)**, and **CGLIB-by-default proxying (Boot 2.0 onward), which invalidates every
pre-2018 "Spring uses JDK proxies when there is an interface" answer**.

Scope boundary against the sibling guides. This file owns **the container, the proxy, and Boot's
bootstrap**: bean definitions, dependency injection, scopes, lifecycle, extension points, AOP,
declarative transaction *mechanics*, events, `Environment`/`PropertySource`, SpEL, conversion,
auto-configuration, and the startup/shutdown sequence. The persistence-context side of
`@Transactional` — flush, dirty checking, `LazyInitializationException`, N+1, open-session-in-view —
lives in `08-spring-data-jpa.md`. Isolation levels, MVCC anomalies, deadlocks and connection-pool
sizing live in `09-sql-databases.md`. Thread pools, `ThreadLocal` semantics, the memory model and
virtual threads live in `05-multithreading-concurrency.md`. REST contract shape, status codes and
`ProblemDetail` as an API decision live in `12-api-design.md`. The Spring Security filter chain,
OAuth2 and method security live in `13-web-security.md`. The cache stores themselves (Redis,
Caffeine, stampede) live in `15-caching.md`. Test slices, Mockito and Testcontainers live in
`16-testing.md`. Classloading, CGLIB's bytecode generation and JIT effects live in
`06-jvm-internals.md`. Where a concept is owned elsewhere the leaf carries `[X-REF nn]`, and the
bible states the mechanism in one paragraph *before* pointing away — it never sends the reader off
empty-handed.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | work the argument through; do not state the result and move on |
| `[SOURCE]` | quote real Spring source, reference-doc text or javadoc (short excerpt) and explain every line |
| `[BUILD]` | ship complete, compiling, generic Java 21 code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 6.2/3.5 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | state the number, default value or byte arithmetic explicitly |
| `[PROP]` | give the exact property key and its default |
| `[API]` | give the exact type/method/attribute signature |
| `[FLOW]` | must be rendered as an ordered step-by-step trace, not prose |
| `[DIAG]` | must show real output — a stack trace, a conditions report, a log line — and read it line by line |

---

# PART 1 — BASICS

## §1.1 Why an IoC container exists at all

1.1.1 The 2002 problem statement: enterprise Java (EJB 2.x) required components to implement
      container interfaces, be deployed to an application server, and be tested only inside one.
      Spring's thesis was "plain objects, container-agnostic, wired externally".
1.1.2 Inversion of Control stated precisely: the *control* being inverted is over **object graph
      construction and lifetime**, not over program flow generally. `[PROVE]`
1.1.3 Dependency injection is one *form* of IoC; service locator is another. Contrast them and say
      why DI wins: dependencies become visible in the signature instead of hidden in a lookup call.
      `[PROVE]`
1.1.4 The four things a container buys you: single-place assembly, lifetime management,
      cross-cutting interception, and substitutability for tests. `[X-REF 16]`
1.1.5 The three things it costs you: startup time proportional to the graph, indirection that
      breaks "jump to implementation", and a whole second failure surface (wiring errors, condition
      mismatches) that a `new` expression does not have.
1.1.6 "Spring is a container plus a set of integrations." Name the module split you actually see on
      a classpath: `spring-core`, `spring-beans`, `spring-context`, `spring-aop`, `spring-aspects`,
      `spring-expression`, `spring-tx`, `spring-jdbc`, `spring-orm`, `spring-web`,
      `spring-webmvc`, `spring-webflux`, `spring-test`. `[API]`
1.1.7 Spring Framework versus Spring Boot versus Spring Cloud versus the Spring portfolio
      (Data, Security, Batch, Integration) — which one owns which decision.
1.1.8 The `jakarta.*` migration: Spring Framework 6 / Boot 3 moved off `javax.*` wholesale. This is
      the single largest breaking change of the 5→6 boundary and why old blog code does not
      compile. `[VERSION-TRAP]`
1.1.9 Baselines: Framework 6.x requires Java 17+, Boot 3.x requires Java 17+, Framework 7 / Boot 4
      keep the Java 17 baseline while targeting Java 25 LTS. `[NUM]` `[RESEARCH]` `[VERSION-TRAP]`
1.1.10 The JSR-330 overlap: `@Inject`, `@Named`, `@Singleton`, `Provider<T>` are supported as
       drop-ins; state exactly where semantics differ from `@Autowired`/`@Qualifier`/`ObjectProvider`.
       `[API]`
1.1.11 The interview framing this whole guide serves: turning "the annotation didn't work" into a
       named mechanism — proxy, lifecycle phase, condition, or property precedence.

*(11 leaves)*

## §1.2 The container types and the interface hierarchy

1.2.1 `BeanFactory` as the root contract: `getBean`, `containsBean`, `isSingleton`, `isPrototype`,
      `getType`, `getAliases`. Lazy by default, no context features. `[API]` `[SOURCE]`
1.2.2 `ApplicationContext extends ListableBeanFactory, HierarchicalBeanFactory, MessageSource,
      ApplicationEventPublisher, ResourcePatternResolver, EnvironmentCapable`. Read the interface
      list as a feature list. `[API]` `[SOURCE]`
1.2.3 The BeanFactory-vs-ApplicationContext comparison table the reference doc publishes:
      bean instantiation/wiring, lifecycle callbacks, `BeanPostProcessor` auto-registration,
      `BeanFactoryPostProcessor` auto-registration, convenient `MessageSource` access, built-in
      `ApplicationEvent` publication. `[SOURCE]` `[RESEARCH]`
1.2.4 `ListableBeanFactory` (`getBeanNamesForType`, `getBeansOfType`,
      `getBeanNamesForAnnotation`, `getBeansWithAnnotation`) — the introspection surface you use in
      diagnostics. `[API]`
1.2.5 `HierarchicalBeanFactory` and parent contexts: child sees parent beans, parent never sees
      child. Where this actually appears — root `WebApplicationContext` vs servlet context,
      Spring Boot's `bootstrapContext`. `[TRAP]`
1.2.6 `ConfigurableApplicationContext`: `refresh()`, `close()`, `registerShutdownHook()`,
      `getBeanFactory()`, `addBeanFactoryPostProcessor()`, `setParent()`. `[API]`
1.2.7 `AutowireCapableBeanFactory` — the escape hatch for injecting into objects the container did
      not create (`autowireBean`, `initializeBean`, `createBean`, `applyBeanPostProcessors*`).
      `[API]`
1.2.8 The concrete context implementations and when each is used:
      `AnnotationConfigApplicationContext`, `GenericApplicationContext`,
      `ClassPathXmlApplicationContext`, `FileSystemXmlApplicationContext`,
      `AnnotationConfigServletWebServerApplicationContext`,
      `AnnotationConfigReactiveWebServerApplicationContext`,
      `GenericWebApplicationContext`, `StaticApplicationContext`. `[API]`
1.2.9 `DefaultListableBeanFactory` as the one implementation that actually holds the beans —
      every `ApplicationContext` wraps one. `[SOURCE]`
1.2.10 Refreshable versus non-refreshable contexts: `AbstractRefreshableApplicationContext`
       discards and rebuilds the internal factory, `GenericApplicationContext` allows exactly one
       `refresh()`. Calling `refresh()` twice on the latter throws
       `IllegalStateException: GenericApplicationContext does not support multiple refresh
       attempts`. `[TRAP]` `[DIAG]`
1.2.11 The context as an `AutoCloseable`: try-with-resources on a standalone context, and what
       `close()` actually triggers (§1.9.14).
1.2.12 Spring Boot's `WebApplicationType` detection algorithm: Spring MVC on classpath → servlet
       context; WebFlux only → reactive context; neither → plain
       `AnnotationConfigApplicationContext`. Override with
       `SpringApplication.setWebApplicationType(NONE)` or `spring.main.web-application-type`.
       `[FLOW]` `[PROP]` `[RESEARCH]`
1.2.13 `getBean(Class)` vs `getBean(String)` vs `getBean(String, Class)` vs
       `getBeanProvider(Class)`, and why calling `getBean` from application code is a design smell
       (service-locator regression, §1.1.3). `[API]` `[TRAP]`

*(13 leaves)*

## §1.3 BeanDefinition — the metadata model

1.3.1 A bean is **not** an object. A bean is a `BeanDefinition` registered under one or more names,
      plus zero or more instances the container derives from it. State this before anything else.
      `[TRAP]`
1.3.2 The `BeanDefinition` property surface, named: `beanClassName`, `scope`, `lazyInit`,
      `dependsOn`, `autowireCandidate`, `primary`, `fallback`, `factoryBeanName`,
      `factoryMethodName`, `constructorArgumentValues`, `propertyValues`, `initMethodName`,
      `destroyMethodName`, `role`, `description`, `source`. `[API]` `[SOURCE]`
1.3.3 `BeanDefinition.ROLE_APPLICATION = 0`, `ROLE_SUPPORT = 1`, `ROLE_INFRASTRUCTURE = 2` — the
      constant that hides framework beans from the actuator `beans` endpoint. `[NUM]` `[API]`
1.3.4 The implementation hierarchy: `AbstractBeanDefinition` → `RootBeanDefinition`,
      `ChildBeanDefinition`, `GenericBeanDefinition`, `AnnotatedGenericBeanDefinition`,
      `ScannedGenericBeanDefinition`, `ConfigurationClassBeanDefinition`. `[API]`
1.3.5 **Merged** bean definitions: `getMergedBeanDefinition` flattens parent/child into a
      `RootBeanDefinition`, and that merged copy is what creation actually reads. `[SOURCE]`
1.3.6 `BeanDefinitionRegistry`: `registerBeanDefinition`, `removeBeanDefinition`,
      `getBeanDefinition`, `containsBeanDefinition`, `getBeanDefinitionNames`,
      `getBeanDefinitionCount`, `isBeanNameInUse`. `[API]`
1.3.7 `BeanDefinitionBuilder` — the fluent way to build one programmatically, and where you would
      (an `ImportBeanDefinitionRegistrar`, a `BeanDefinitionRegistryPostProcessor`). `[API]`
1.3.8 `BeanDefinitionOverrideException` and `spring.main.allow-bean-definition-overriding` (default
      **false** since Boot 2.1). What the pre-2.1 silent-overwrite behaviour used to hide.
      `[PROP]` `[NUM]` `[VERSION-TRAP]` `[TRAP]`
1.3.9 Bean naming rules: `@Component("name")`, `@Bean` method name, and the default
      `AnnotationBeanNameGenerator` decapitalisation rule — including the JavaBeans exception where
      two leading capitals are preserved (`URLHandler` → `URLHandler`, not `uRLHandler`).
      `[TRAP]` `[NUM]`
1.3.10 `FullyQualifiedAnnotationBeanNameGenerator` as the fix for same-simple-name classes in
       different packages colliding. `[API]`
1.3.11 Aliases: `@Bean(name = {"a","b"})`, `registerAlias`, `<alias>`, and `getAliases`.
1.3.12 `@DependsOn` — forces *initialisation order* without a reference, the only tool for
       "this static-registering bean must exist first". Not a substitute for injection. `[TRAP]`
1.3.13 `@Lazy` on a definition vs `@Lazy` at an injection point: the first defers creation, the
       second injects a lazy-resolution proxy. Materially different mechanisms. `[TRAP]`
1.3.14 `@Role`, `@Description`, `@Order` and `@Priority` as definition-level metadata, and which of
       them affect resolution versus documentation only.
1.3.15 `spring.main.lazy-initialization=true` as a global switch, `@Lazy(false)` as the per-bean
       opt-out, and the trade it makes (fast startup, late failure). `[PROP]` `[TRAP]`

*(15 leaves)*

## §1.4 Where definitions come from — configuration metadata

1.4.1 The four sources: XML (`<bean>`), annotated classes found by component scanning,
      `@Bean` methods in `@Configuration` classes, and programmatic registration.
1.4.2 XML is not dead, it is *unused* — say where you still meet it (legacy apps, `spring-config`
      in older Batch/Integration setups) and read a `<bean>` element's attributes once. `[SOURCE]`
1.4.3 `@Configuration` + `@Bean` as the modern default, and `@ComponentScan` as the discovery
      mechanism.
1.4.4 `@ComponentScan` attributes in full: `basePackages`, `basePackageClasses`,
      `nameGenerator`, `scopeResolver`, `scopedProxy`, `resourcePattern`,
      `useDefaultFilters`, `includeFilters`, `excludeFilters`, `lazyInit`. `[API]`
1.4.5 `@ComponentScan.Filter` types: `ANNOTATION`, `ASSIGNABLE_TYPE`, `ASPECTJ`, `REGEX`, `CUSTOM`.
      `[API]`
1.4.6 The default include filters: `@Component` (and anything meta-annotated with it),
      plus `@ManagedBean` / `@Named` when JSR-330 is present. `useDefaultFilters = false` turns all
      of that off. `[TRAP]`
1.4.7 `ClassPathBeanDefinitionScanner` and `ClassPathScanningCandidateComponentProvider` — the
      actual scanner; it reads **ASM metadata**, not loaded classes, which is why scanning does not
      trigger static initialisers. `[SOURCE]` `[X-REF 06]`
1.4.8 The `spring.components` index (`CandidateComponentsIndex`, generated by
      `spring-context-indexer`) as a scan-time optimisation, and why Boot's own code prefers
      explicit imports over scanning. `[RESEARCH]`
1.4.9 `@SpringBootApplication` scans **its own package and all sub-packages**. Putting the main
      class in a leaf package is the #1 cause of "my `@Service` isn't found". `[TRAP]`
1.4.10 `@Import` — importing a `@Configuration` class, a plain component class, an
       `ImportSelector`, a `DeferredImportSelector`, or an `ImportBeanDefinitionRegistrar`. Four
       distinct behaviours behind one annotation. `[API]` `[TRAP]`
1.4.11 `ImportSelector.selectImports(AnnotationMetadata)` versus
       `DeferredImportSelector` (+ `Group`) — the latter runs **after** all regular configuration
       is processed, which is exactly what makes `@ConditionalOnMissingBean` in auto-configuration
       work. `[PROVE]` `[SOURCE]`
1.4.12 `ImportBeanDefinitionRegistrar.registerBeanDefinitions(AnnotationMetadata,
       BeanDefinitionRegistry)` — how Spring Data, MyBatis and `@MapperScan` register repositories
       that have no implementation class. `[API]` `[X-REF 08]`
1.4.13 `@ImportResource` for mixing XML into annotation config.
1.4.14 `@Enable*` annotations as a convention: each is `@Import` of a selector or configuration
       (`@EnableTransactionManagement`, `@EnableAsync`, `@EnableScheduling`, `@EnableCaching`,
       `@EnableAspectJAutoProxy`, `@EnableWebMvc`, `@EnableConfigurationProperties`). `[API]`
1.4.15 `AdviceMode.PROXY` vs `AdviceMode.ASPECTJ` as a shared attribute of the `@Enable*` family,
       and what changing it actually swaps in. `[API]`
1.4.16 Programmatic registration paths: `context.registerBean(Class, Supplier)`,
       `GenericApplicationContext.registerBean`, and (7.0) `BeanRegistrar`.
       `[API]` `[VERSION-TRAP]` `[RESEARCH]`
1.4.17 `FactoryBean<T>`: `getObject()`, `getObjectType()`, `isSingleton()`. The `&` prefix retrieves
       the factory itself rather than the product. This is how `SqlSessionFactoryBean`,
       `LocalContainerEntityManagerFactoryBean` and `ProxyFactoryBean` all work. `[API]` `[TRAP]`
1.4.18 `FactoryBean` versus a `@Bean` factory method: the former participates in type matching
       before the product exists (via `getObjectType()`), which matters for
       `@ConditionalOnMissingBean` and for autowiring by type. `[PROVE]`

*(18 leaves)*

## §1.5 Stereotypes and meta-annotations

1.5.1 The stereotype table with the *real* mechanical difference:
      `@Component` (nothing), `@Service` (nothing — semantic marker only),
      `@Repository` (**exception translation**), `@Controller` (MVC handler detection),
      `@RestController` (`@Controller` + `@ResponseBody`), `@Configuration` (CGLIB enhancement),
      `@ControllerAdvice` / `@RestControllerAdvice`. `[TRAP]`
1.5.2 `@Repository`'s mechanism named precisely:
      `PersistenceExceptionTranslationPostProcessor` adds a
      `PersistenceExceptionTranslationAdvisor`, which delegates to
      `PersistenceExceptionTranslator` implementations (e.g. `HibernateExceptionTranslator`,
      `SessionFactoryUtils`) to convert vendor exceptions into Spring's `DataAccessException`
      hierarchy. `[SOURCE]` `[API]`
1.5.3 The `DataAccessException` hierarchy worth naming:
      `DataIntegrityViolationException`, `DuplicateKeyException`,
      `OptimisticLockingFailureException`, `PessimisticLockingFailureException`,
      `CannotAcquireLockException`, `DeadlockLoserDataAccessException`,
      `QueryTimeoutException`, `EmptyResultDataAccessException`,
      `IncorrectResultSizeDataAccessException`, `BadSqlGrammarException`,
      `TransientDataAccessResourceException`. `[API]` `[X-REF 09]`
1.5.4 Why the translation matters architecturally: your service layer never imports
      `org.hibernate` or catches `SQLException`. `[PROVE]`
1.5.5 Meta-annotation composition: Spring's `@AliasFor`, `MergedAnnotations`,
      `AnnotatedElementUtils.findMergedAnnotation`. This is why `@RestController` behaves as both
      of its parts and why your own composed annotations work. `[API]` `[SOURCE]`
1.5.6 `@AliasFor` in both forms — aliasing within one annotation, and aliasing an attribute of a
      meta-annotation. `[API]`
1.5.7 Building a composed annotation of your own (e.g. `@TransactionalService` =
      `@Service` + `@Transactional(readOnly=true)`), and the attribute-override rules.
1.5.8 Annotation *retention* requirement: Spring only sees `RetentionPolicy.RUNTIME`. A `SOURCE`
      or `CLASS` retention annotation is invisible to the container. `[X-REF 06]` `[TRAP]`
1.5.9 `@Indexed` and how it feeds the components index (§1.4.8).
1.5.10 **Trap:** "changing `@Service` to `@Component` breaks things." It does not. Changing
       `@Repository` to `@Component` silently removes exception translation. `[TRAP]`

*(10 leaves)*

## §1.6 Dependency injection — the three styles

1.6.1 Constructor injection: the mechanism (`createBeanInstance` resolves constructor args, then
      calls the constructor) and the four independent arguments for it — immutability (`final`
      fields), no half-built object, container-free unit tests, visible SRP pressure.
      `[PROVE]` `[X-REF 16]`
1.6.2 Since Spring 4.3, a class with **exactly one** constructor needs no `@Autowired`. State the
      version. `[VERSION-TRAP]` `[NUM]`
1.6.3 The full constructor-selection algorithm: single constructor → used; multiple with exactly
      one `@Autowired(required=true)` → that one; multiple all `@Autowired(required=false)` →
      greediest satisfiable; otherwise default/primary constructor. `[FLOW]` `[SOURCE]`
      `[RESEARCH]`
1.6.4 Setter injection: the mechanism (`populateBean` → `InjectionMetadata` → reflective setter
      call) and its one legitimate use — genuinely optional, reconfigurable dependencies.
1.6.5 Field injection: `AutowiredAnnotationBeanPostProcessor` walks fields, calls
      `Field.setAccessible(true)`, and assigns. Why the field cannot be `final`. `[SOURCE]`
      `[PROVE]`
1.6.6 **Trap:** "field injection is fine, Spring handles it." The cost is not runtime failure —
      it is untestable classes and *masked* circular dependencies that constructor injection would
      have failed loudly on. `[TRAP]`
1.6.7 Method injection with arbitrary names and multiple arguments (`@Autowired` on any method).
1.6.8 `@Autowired(required = false)` semantics: non-required *methods* are not called at all;
      non-required *fields* keep their default value. `[API]` `[TRAP]`
1.6.9 `Optional<T>` and `@Nullable` at an injection point as the modern spelling of optional.
      Spring accepts `@Nullable` from any package, including `org.jspecify.annotations.Nullable`.
      `[API]` `[RESEARCH]`
1.6.10 `@Value` at an injection point — property, SpEL, default (`${a.b:fallback}`), and its
       conversion path through `ConversionService` (§1.18). `[API]`
1.6.11 `@Resource` (JSR-250): matches **by name first**, then by type — the opposite default from
       `@Autowired`. `@Inject` (JSR-330): equivalent to `@Autowired` but with no `required`
       attribute. `[TRAP]` `[API]`
1.6.12 `CommonAnnotationBeanPostProcessor` as the processor behind `@Resource`, `@PostConstruct`
       and `@PreDestroy`; in Jakarta these live in `jakarta.annotation` and need
       `jakarta.annotation-api` on the classpath. `[VERSION-TRAP]`
1.6.13 Collection injection: `List<T>`, `Set<T>`, `T[]`, `Map<String,T>` (keys = bean names) — the
       canonical strategy/plugin registry. Order comes from `@Order` / `Ordered`, **not**
       declaration order. `[API]` `[TRAP]`
1.6.14 Empty-collection semantics: an injected collection with no candidates fails by default at a
       constructor arg but resolves to an empty collection for multi-element injection points —
       state the exact rule. `[RESEARCH]` `[TRAP]`
1.6.15 `ObjectProvider<T>` full surface: `getObject()`, `getObject(Object...)`, `getIfAvailable()`,
       `getIfAvailable(Supplier)`, `getIfUnique()`, `ifAvailable(Consumer)`, `stream()`,
       `orderedStream()`. The lazy, optional, multi-candidate injection point. `[API]`
1.6.16 `ObjectFactory<T>` and JSR-330 `Provider<T>` as the older, thinner versions of the same idea.
1.6.17 `@Lookup` method injection: Spring CGLIB-overrides an abstract or concrete method to return a
       fresh container lookup on each call. Requires a non-final, non-private method. `[API]`
       `[TRAP]`
1.6.18 Well-known resolvable dependencies injectable without any bean definition:
       `BeanFactory`, `ApplicationContext`, `Environment`, `ResourceLoader`,
       `ApplicationEventPublisher`, `MessageSource`. Registered via
       `beanFactory.registerResolvableDependency` in `prepareBeanFactory`. `[SOURCE]` `[API]`
1.6.19 Self-injection: allowed, but only as a **fallback** candidate with lowest precedence; never
       primary. Its real use is obtaining your own proxy (§2.5). `[SOURCE]` `[TRAP]`
1.6.20 **Trap:** `@Autowired` on a field of a `BeanPostProcessor` or `BeanFactoryPostProcessor` is
       not honoured reliably — those beans are created before the annotation processors are in
       place. Wire them via constructor args on a `@Bean` method. `[TRAP]` `[SOURCE]`
1.6.21 Circular dependency by constructor is unresolvable; by field/setter it is resolvable via the
       early-reference cache (§3.4). `[X-REF §3.4]`
1.6.22 Injecting a generic type: `Repository<Order>` vs `Repository<User>` resolves correctly
       because `ResolvableType` carries the generic signature from the `Signature` class-file
       attribute. `[X-REF 06]` `[PROVE]`

*(22 leaves)*

## §1.7 Autowire candidate resolution and ambiguity

1.7.1 The resolution algorithm in order: find all beans assignable to the required type → filter by
      `autowireCandidate` → filter by qualifiers → apply `@Primary` → apply `@Fallback` exclusion →
      apply `@Priority` → match by field/parameter name against bean name → else
      `NoUniqueBeanDefinitionException`. `[FLOW]` `[SOURCE]`
1.7.2 `NoSuchBeanDefinitionException` vs `NoUniqueBeanDefinitionException` vs
      `UnsatisfiedDependencyException` — three different messages, three different causes. Read one
      of each. `[DIAG]` `[TRAP]`
1.7.3 `@Qualifier("name")` — matches a bean's qualifier value *or*, failing that, its bean name.
      `[API]`
1.7.4 Custom qualifier annotations: meta-annotate with `@Qualifier`, e.g. `@Fast`, `@AuditLog`.
      The type-safe alternative to string names. `[API]`
1.7.5 `@Primary` — the default winner when several candidates match.
1.7.6 `@Fallback` (Spring Framework **6.2**, new): marks a bean as used only when no other
      candidate of that type exists. The inverse of `@Primary`, and the thing auto-configurations
      wanted all along. `[API]` `[RESEARCH]` `[VERSION-TRAP]`
1.7.7 `@Priority` (JSR-250) — supported on classes, **not** on `@Bean` methods; lower value wins.
      `[TRAP]` `[API]`
1.7.8 Parameter-name matching as the last-resort tiebreak, and why it silently breaks when the code
      is compiled without `-parameters`. Spring Boot's parent POM adds `-parameters`; a hand-rolled
      build may not. `[TRAP]` `[NUM]`
1.7.9 Generic-type matching as an implicit qualifier (`Converter<String, Order>`).
1.7.10 `autowireCandidate = false` / `@Bean(autowireCandidate = false)` — present in the context,
       invisible to by-type autowiring.
1.7.11 `@Order` / `Ordered` / `PriorityOrdered` on collection injection ordering, and the fact that
       none of them affect **singleton startup order** — that is determined by dependency edges and
       `@DependsOn`. `[TRAP]` `[SOURCE]`
1.7.12 `Ordered.HIGHEST_PRECEDENCE = Integer.MIN_VALUE`, `LOWEST_PRECEDENCE = Integer.MAX_VALUE`,
       default order for unannotated = `LOWEST_PRECEDENCE`. `[NUM]` `[API]`
1.7.13 `AnnotationAwareOrderComparator` versus `OrderComparator` — the former also reads `@Order`
       and `@Priority`. `[API]`
1.7.14 Autowiring modes from the XML era (`no`, `byName`, `byType`, `constructor`) and why they are
       historical trivia now. `[VERSION-TRAP]`

*(14 leaves)*

## §1.8 Scopes

1.8.1 The six built-in scopes and their identifiers: `singleton`, `prototype`, `request`,
      `session`, `application`, `websocket`. Plus `thread` via `SimpleThreadScope`, which is
      **not registered by default**. `[API]` `[RESEARCH]`
1.8.2 `singleton` means **one per container**, not one per JVM and not one per classloader. Two
      contexts in one JVM give two instances. `[TRAP]`
1.8.3 The singleton-statefulness data race: mutable instance state on a singleton is shared across
      every request thread. Show the buggy `List<Row> buffer` field, the interleaving, and the fix
      (method-local state). `[TRAP]` `[X-REF 05]`
1.8.4 `prototype`: new instance per lookup, dependencies injected, `@PostConstruct` **is** called —
      but the container keeps no reference, so `@PreDestroy` / `DisposableBean` is **never**
      called. `[TRAP]` `[SOURCE]`
1.8.5 The prototype-in-singleton capture bug: the singleton is wired once, so it holds exactly one
      prototype instance forever. `[TRAP]`
1.8.6 The four fixes ranked: `ObjectProvider`/`ObjectFactory`/`Provider` per-call lookup,
      `@Lookup`, scoped proxy, or `ApplicationContextAware` + `getBean` (worst).
1.8.7 `request` scope: one instance per HTTP request, destruction callback fires at request
      completion. `@RequestScope` is the composed shortcut.
1.8.8 `session` scope and `@SessionScope`; destruction at session end; the serialization
      requirement when sessions are clustered. `[TRAP]`
1.8.9 `application` scope and `@ApplicationScope`: one per **`ServletContext`**, exposed as a
      servlet-context attribute — not the same thing as a singleton per `ApplicationContext`.
      `[TRAP]`
1.8.10 `websocket` scope, bound to the WebSocket session (STOMP).
1.8.11 `RequestContextHolder` and how request-scoped state is actually bound: a `ThreadLocal`
       (`RequestContextHolder.requestAttributes`) plus an inheritable variant.
       `[SOURCE]` `[X-REF 05]`
1.8.12 `RequestContextListener` / `RequestContextFilter` — required only outside
       `DispatcherServlet`-served requests; `DispatcherServlet` binds the attributes itself.
       `[TRAP]`
1.8.13 The scoped proxy: `@Scope(value="request", proxyMode = ScopedProxyMode.TARGET_CLASS)`.
       `ScopedProxyMode` values: `NO`, `DEFAULT`, `INTERFACES`, `TARGET_CLASS`. `[API]`
1.8.14 What the scoped proxy actually is: a `ScopedProxyFactoryBean` producing a proxy whose
       `TargetSource` is a `SimpleBeanTargetSource` resolving the real instance from the `Scope` on
       every call. `[SOURCE]` `[PROVE]`
1.8.15 The `Scope` SPI: `get(String, ObjectFactory<?>)`, `remove(String)`,
       `registerDestructionCallback(String, Runnable)`, `resolveContextualObject(String)`,
       `getConversationId()`. `[API]` `[SOURCE]`
1.8.16 Registering a custom scope: `beanFactory.registerScope(name, scope)` or
       `CustomScopeConfigurer`. A worked tenant-scope example. `[API]`
1.8.17 The destruction-callback table per scope — which scopes call `@PreDestroy` and which do not.
1.8.18 **Trap:** accessing a request-scoped bean from an `@Async` thread or a `@Scheduled` job
       throws `IllegalStateException: No thread-bound request found`. `[TRAP]` `[DIAG]`
       `[X-REF 05]`
1.8.19 Scope and virtual threads: `spring.threads.virtual.enabled=true` changes which threads carry
       the request `ThreadLocal`; `InheritableThreadLocal` does not propagate to virtual threads
       created by the platform executor in the way people assume. `[PROP]` `[X-REF 05]`
       `[RESEARCH]`

*(19 leaves)*

## §1.9 The bean lifecycle, end to end

1.9.1 The canonical ordered list for a singleton, every step named:
      instantiation (constructor + constructor injection) → populate (field/setter injection) →
      `BeanNameAware` → `BeanClassLoaderAware` → `BeanFactoryAware` → remaining `*Aware` via
      `ApplicationContextAwareProcessor` → `BeanPostProcessor.postProcessBeforeInitialization` →
      `@PostConstruct` → `InitializingBean.afterPropertiesSet()` → custom `initMethod` →
      `BeanPostProcessor.postProcessAfterInitialization` (**where AOP proxies are created**) →
      `SmartInitializingSingleton.afterSingletonsInstantiated()` (after *all* singletons) →
      in use → `SmartLifecycle.start()` → `SmartLifecycle.stop()` → `@PreDestroy` →
      `DisposableBean.destroy()` → custom `destroyMethod`. `[FLOW]` `[SOURCE]`
1.9.2 The complete `Aware` inventory and what each hands you: `BeanNameAware`,
      `BeanClassLoaderAware`, `BeanFactoryAware`, `EnvironmentAware`, `EmbeddedValueResolverAware`,
      `ResourceLoaderAware`, `ApplicationEventPublisherAware`, `MessageSourceAware`,
      `ApplicationStartupAware`, `ApplicationContextAware`, `ServletConfigAware`,
      `ServletContextAware`, `LoadTimeWeaverAware`, `NotificationPublisherAware`,
      `ImportAware`. `[API]` `[SOURCE]` `[RESEARCH]`
1.9.3 Which `Aware` callbacks are invoked directly in `invokeAwareMethods` (three of them) and
      which arrive via `ApplicationContextAwareProcessor` — a real distinction visible in a stack
      trace. `[SOURCE]`
1.9.4 `@PostConstruct` semantics: no args, any visibility, `void`, may throw; runs once; inherited
      methods run too. `[API]`
1.9.5 The three initialisation mechanisms and their fixed relative order (`@PostConstruct` →
      `afterPropertiesSet` → `initMethod`), and why you should pick exactly one. `[TRAP]`
1.9.6 `@Bean(initMethod = "...", destroyMethod = "...")` and the **inferred** destroy method:
      Spring calls a public no-arg `close()` or `shutdown()` automatically. Disable with
      `destroyMethod = ""`. This is the single most surprising default in `@Bean`. `[TRAP]`
      `[NUM]` `[API]`
1.9.7 **Trap:** calling a `@Transactional`/`@Cacheable`/`@Async` method from your own
      `@PostConstruct`. Two reasons it fails: the proxy does not exist yet at that point, and you
      are on the raw instance regardless. `[TRAP]` `[PROVE]`
1.9.8 `SmartInitializingSingleton.afterSingletonsInstantiated()` as the correct "all singletons are
      ready" hook inside the container. `[API]`
1.9.9 `ApplicationRunner` and `CommandLineRunner` run **after** refresh completes and after
      `ApplicationStartedEvent`; ordered by `@Order`; an exception in one fails the application.
      The right place for startup work needing proxies or transactions. `[API]` `[TRAP]`
1.9.10 `Lifecycle` (`start`, `stop`, `isRunning`), `SmartLifecycle` (`isAutoStartup`,
       `stop(Runnable)`, `getPhase`), `Phased`. `[API]` `[SOURCE]`
1.9.11 Phase semantics: **lowest phase starts first and stops last**; default phase for a
       non-`SmartLifecycle` is `0`; `SmartLifecycle.DEFAULT_PHASE = Integer.MAX_VALUE`. `[NUM]`
       `[TRAP]` `[RESEARCH]`
1.9.12 `DefaultLifecycleProcessor` (bean name `lifecycleProcessor`), `timeoutPerShutdownPhase`
       default **30000 ms**; Boot's `spring.lifecycle.timeout-per-shutdown-phase` (default `30s`).
       `[NUM]` `[PROP]` `[RESEARCH]`
1.9.13 Graceful shutdown in Boot: `server.shutdown=graceful`, implemented as the earliest
       `SmartLifecycle` stop phase; existing requests drain, new ones are rejected. `[PROP]`
       `[RESEARCH]`
1.9.14 `close()`: publishes `ContextClosedEvent` → stops `Lifecycle` beans → destroys singletons in
       **reverse dependency order** → closes the bean factory → closes the parent-independent
       resources. `[FLOW]` `[SOURCE]`
1.9.15 `registerShutdownHook()` and what it registers on the JVM (`Runtime.addShutdownHook`), plus
       the SIGKILL / `OOMKilled` case where it never runs at all. `[X-REF 06]` `[X-REF 19]`
1.9.16 `DisposableBeanAdapter` — the object that remembers which of the three destroy mechanisms
       apply to each bean. `[SOURCE]`
1.9.17 Lifecycle of a `@Bean`-produced third-party object versus a scanned `@Component`: identical
       from the container's point of view, which is the point.
1.9.18 Background bean initialisation (Framework 6.2): `@Bean(bootstrap = Bean.Bootstrap.BACKGROUND)`
       plus a `bootstrapExecutor` bean; Boot 3.5 auto-configures `bootstrapExecutor` when
       `applicationTaskExecutor` exists. Non-lazy dependents block until it completes.
       `[API]` `[RESEARCH]` `[VERSION-TRAP]`

*(18 leaves)*

## §1.10 The container extension points

1.10.1 The two-phase model stated once: **definition phase** (`BeanFactoryPostProcessor` mutates
       `BeanDefinition`s; nothing is instantiated) then **instance phase**
       (`BeanPostProcessor` sees objects). Every extension question reduces to "which phase". 
       `[PROVE]`
1.10.2 `BeanFactoryPostProcessor.postProcessBeanFactory(ConfigurableListableBeanFactory)`. `[API]`
1.10.3 `BeanDefinitionRegistryPostProcessor.postProcessBeanDefinitionRegistry(BeanDefinitionRegistry)`
       — runs **before** all plain BFPPs and is the hook that can add new definitions.
       `ConfigurationClassPostProcessor` is one. `[API]` `[SOURCE]`
1.10.4 `PropertySourcesPlaceholderConfigurer` as the canonical BFPP — it resolves `${...}` inside
       bean definitions. Must be a `static @Bean` method when declared in a `@Configuration` class,
       and the reason is that a BFPP must be created before the configuration class it lives in.
       `[TRAP]` `[PROVE]`
1.10.5 `BeanPostProcessor.postProcessBeforeInitialization` /
       `postProcessAfterInitialization` — both default to returning the bean unchanged since
       Java 8 default methods. `[API]` `[SOURCE]`
1.10.6 `InstantiationAwareBeanPostProcessor`:
       `postProcessBeforeInstantiation` (can short-circuit creation entirely),
       `postProcessAfterInstantiation`, `postProcessProperties`. `[API]`
1.10.7 `SmartInstantiationAwareBeanPostProcessor`: `predictBeanType`,
       `determineCandidateConstructors`, `getEarlyBeanReference` — the last is the hook that makes
       AOP-plus-circular-dependency work at all (§3.4). `[API]` `[SOURCE]`
1.10.8 `MergedBeanDefinitionPostProcessor.postProcessMergedBeanDefinition` — where
       `AutowiredAnnotationBeanPostProcessor` and `CommonAnnotationBeanPostProcessor` build their
       `InjectionMetadata` caches. `[SOURCE]`
1.10.9 `DestructionAwareBeanPostProcessor.postProcessBeforeDestruction`.
1.10.10 The **built-in** post-processors you should be able to name and place:
        `ConfigurationClassPostProcessor`, `AutowiredAnnotationBeanPostProcessor`,
        `CommonAnnotationBeanPostProcessor`, `ApplicationContextAwareProcessor`,
        `ApplicationListenerDetector`, `AnnotationAwareAspectJAutoProxyCreator`,
        `InfrastructureAdvisorAutoProxyCreator`, `PersistenceExceptionTranslationPostProcessor`,
        `AsyncAnnotationBeanPostProcessor`, `ScheduledAnnotationBeanPostProcessor`,
        `ConfigurationPropertiesBindingPostProcessor`, `MethodValidationPostProcessor`,
        `EventListenerMethodProcessor`, `PersistenceAnnotationBeanPostProcessor`,
        `LoadTimeWeaverAwareProcessor`. `[API]` `[RESEARCH]`
1.10.11 BPP ordering: `PriorityOrdered` first, then `Ordered`, then the rest — **programmatically
        registered** BPPs ignore ordering annotations and run in registration order. `[SOURCE]`
        `[TRAP]` `[RESEARCH]`
1.10.12 **Trap:** any bean that a `BeanPostProcessor` depends on is instantiated early, before the
        full BPP set is registered, and therefore **cannot be proxied**. Symptom: a `@Transactional`
        `DataSource`-touching bean silently loses its advice. Boot logs
        `Bean 'x' of type [...] is not eligible for getting processed by all BeanPostProcessors`.
        `[TRAP]` `[DIAG]` `[SOURCE]`
1.10.13 `ApplicationContextInitializer.initialize(ConfigurableApplicationContext)` — runs before
        `refresh()`; registered via `SpringApplication.addInitializers`, `spring.factories`, or the
        `context.initializer.classes` property. `[API]` `[PROP]`
1.10.14 `EnvironmentPostProcessor` — runs even earlier, before the context exists; registered in
        `META-INF/spring.factories`. The correct hook for injecting a property source from a
        secrets manager. `[API]`
1.10.15 `SpringApplicationRunListener` (`starting`, `environmentPrepared`, `contextPrepared`,
        `contextLoaded`, `started`, `ready`, `failed`). `[API]` `[RESEARCH]`
1.10.16 `FailureAnalyzer` / `FailureAnalysisReporter` — how Boot turns a raw exception into the
        boxed "APPLICATION FAILED TO START / Description / Action" block. `[API]` `[DIAG]`
1.10.17 Choosing the right extension point: a decision table over "mutate a definition", "wrap an
        instance", "add definitions", "add property sources", "run after startup".

*(17 leaves)*

## §1.11 `@Configuration`, `@Bean`, and the two modes

1.11.1 `@Bean` method semantics: return type determines the bean type, method name determines the
       bean name, parameters are injected by type.
1.11.2 `@Bean` attributes: `name`, `value`, `autowire` (deprecated), `autowireCandidate`,
       `initMethod`, `destroyMethod`, `bootstrap`. `[API]`
1.11.3 **Full mode** (`@Configuration`, `proxyBeanMethods = true`, the default): the class is
       CGLIB-enhanced so an inter-`@Bean` call returns the container-managed singleton.
       `[PROVE]` `[SOURCE]`
1.11.4 **Lite mode**: `@Bean` methods on a `@Component`, or `@Configuration(proxyBeanMethods=false)`
       — no enhancement, so an inter-method call is a plain Java call producing a *new* object.
       Boot's own auto-configurations use lite mode for startup speed. `[TRAP]` `[NUM]`
1.11.5 The preferred way to avoid the whole question: take the dependency as a **method parameter**
       instead of calling the sibling `@Bean` method.
1.11.6 Constraints imposed by CGLIB enhancement: the `@Configuration` class may not be `final`, may
       not be a local/anonymous class, must have a callable constructor, and `@Bean` methods may
       not be `private`, `final`, or `static`-with-instance-semantics. `[TRAP]`
1.11.7 `static @Bean` methods: needed for `BeanFactoryPostProcessor` and `BeanPostProcessor`
       definitions so the enclosing configuration class is not forced into early instantiation.
       `[PROVE]` `[TRAP]`
1.11.8 `@Configuration` classes are themselves beans, so they can take constructor injection and
       carry `@Autowired` fields — with the "own beans are fallback candidates" caveat.
       `[RESEARCH]`
1.11.9 `@ImportAware` — how a configuration class reads the attributes of the `@Enable*` annotation
       that imported it. `[API]`
1.11.10 `@Conditional(Condition.class)` at the framework level: `matches(ConditionContext,
        AnnotatedTypeMetadata)`, `ConfigurationCondition` and its two
        `ConfigurationPhase` values (`PARSE_CONFIGURATION`, `REGISTER_BEAN`). `[API]` `[SOURCE]`
1.11.11 `@Profile` is implemented as `@Conditional(ProfileCondition.class)` — profiles are not a
        separate mechanism. `[PROVE]` `[SOURCE]`
1.11.12 Overloaded `@Bean` methods and `@Profile`: only the first declaration's condition is
        considered. A genuine, documented sharp edge. `[TRAP]` `[RESEARCH]`
1.11.13 Two `@Bean` methods with the same declared bean name across configurations — which wins,
        and how `spring.main.allow-bean-definition-overriding` changes the outcome. `[TRAP]`

*(13 leaves)*

## §1.12 The proxy model — the single most important Spring mechanism

1.12.1 The one-sentence statement: **the bean in the context is not your object; it is a proxy that
       runs an interceptor chain and then delegates to your object.** Everything declarative —
       `@Transactional`, `@Cacheable`, `@Async`, `@Retryable`, `@PreAuthorize`, `@Validated`,
       `@Observed` — is this.
1.12.2 The call diagram: caller → proxy → `MethodInterceptor` chain → target instance → back out
       through the chain. `[FLOW]`
1.12.3 JDK dynamic proxy: `java.lang.reflect.Proxy.newProxyInstance`, implements the target's
       interfaces, dispatches through `InvocationHandler`. Cannot advise anything not on an
       interface. `[API]` `[X-REF 06]`
1.12.4 CGLIB proxy: a generated **subclass** overriding every non-final, non-private, non-static
       method and routing it to the interceptor. Spring repackages CGLIB inside
       `org.springframework.cglib` and uses Objenesis to construct without invoking the target
       constructor. `[SOURCE]` `[RESEARCH]`
1.12.5 The selection rule in `DefaultAopProxyFactory`: use CGLIB if `optimize` is set, or
       `proxyTargetClass` is set, or the target has **no** proxyable interfaces; otherwise JDK.
       `[SOURCE]` `[FLOW]`
1.12.6 Spring Boot forces `proxyTargetClass = true` globally
       (`spring.aop.proxy-target-class` default **true** since Boot 2.0) so injecting by concrete
       class always works. Plain Spring's historic default was JDK-when-interface-present.
       `[PROP]` `[NUM]` `[VERSION-TRAP]` `[TRAP]`
1.12.7 The comparison table: requires-an-interface, produces, injectable-as, cannot-advise,
       constructor behaviour, `final` handling, performance, `equals`/`hashCode` handling.
1.12.8 What CGLIB cannot advise, exactly: `final` classes (no proxy at all —
       `IllegalArgumentException: Cannot subclass final class`), `final` methods, `private`
       methods, `static` methods, and package-private methods across packages. The annotation is
       **silently ignored**, with no warning. `[TRAP]` `[DIAG]`
1.12.9 Kotlin's `final`-by-default and the `kotlin-spring` (`allopen`) plugin as the reason Kotlin
       Spring code needs a compiler plugin at all. `[RESEARCH]`
1.12.10 The CGLIB double-construction effect: the subclass constructor runs, and with Objenesis
        the target's own constructor may be skipped or run separately. Never put side effects in a
        proxied bean's constructor, and never read state off the proxy instance's fields — they are
        null/default. `[TRAP]` `[PROVE]`
1.12.11 `this` inside the target is always the raw object. That single fact explains
        self-invocation (§2.5). `[PROVE]`
1.12.12 Injecting a JDK-proxied bean by concrete class fails with
        `BeanNotOfRequiredTypeException: Bean named 'x' is expected to be of type 'XImpl' but was
        actually of type 'com.sun.proxy.$Proxy42'`. `[DIAG]` `[TRAP]`
1.12.13 `AopUtils.isAopProxy`, `isJdkDynamicProxy`, `isCglibProxy`, `AopProxyUtils.ultimateTargetClass`,
        and `AopTestUtils.getTargetObject` / `getUltimateTargetObject` for tests. `[API]`
       `[X-REF 16]`
1.12.14 `@EnableAspectJAutoProxy(proxyTargetClass, exposeProxy)` and `AopContext.currentProxy()`.
        `[API]`
1.12.15 Load-time and compile-time **AspectJ weaving** as the alternative that has none of these
        limits: `@EnableLoadTimeWeaving`, `aspectjweaver`, `spring-aspects`. Why it is rarely worth
        the build complexity. `[X-REF 06]`
1.12.16 Proxy cost: one extra virtual call plus chain iteration per invocation; the JIT usually
        inlines the whole chain for a monomorphic call site. State the honest number — it is not
        the reason your service is slow. `[X-REF 06]` `[PROVE]`

*(16 leaves)*

## §1.13 Spring AOP — vocabulary and API surface

1.13.1 The vocabulary, each defined precisely: aspect, join point, advice, pointcut, introduction,
       target object, AOP proxy, weaving.
1.13.2 Spring AOP supports **method-execution join points only** — no field access, no constructor
       interception, no static initialiser. AspectJ supports all of them. `[TRAP]`
1.13.3 The five advice annotations and their semantics: `@Before`, `@AfterReturning`,
       `@AfterThrowing`, `@After` (finally), `@Around`. `[API]`
1.13.4 Advice precedence **within one aspect**: `@Around` → `@Before` → `@After` →
       `@AfterReturning` → `@AfterThrowing`. `[NUM]` `[RESEARCH]` `[SOURCE]`
1.13.5 Advice precedence **across aspects**: `@Order` / `Ordered`, lower value = higher precedence =
       first on the way in, last on the way out. `[PROVE]`
1.13.6 `JoinPoint` API: `getArgs()`, `getThis()` (the proxy), `getTarget()`, `getSignature()`,
       `getStaticPart()`, `toShortString()`. `[API]`
1.13.7 `ProceedingJoinPoint.proceed()` and `proceed(Object[])` — the argument-rewriting form.
       `[API]`
1.13.8 The pointcut designators Spring AOP actually supports: `execution`, `within`, `this`,
       `target`, `args`, `@target`, `@args`, `@within`, `@annotation`, `bean(name)`. Everything
       else in the AspectJ grammar throws at parse time. `[API]` `[TRAP]` `[RESEARCH]`
1.13.9 The `execution` pattern grammar read symbol by symbol:
       `execution(modifiers? ret-type declaring-type?.name(params) throws?)`, with `*` and `..`
       wildcards. `[SOURCE]`
1.13.10 `this(Type)` matches the **proxy**, `target(Type)` matches the **target** — and with CGLIB
        they are the same class while with JDK proxies they are not. The classic exam distinction.
        `[TRAP]` `[PROVE]`
1.13.11 Named `@Pointcut` methods, combining with `&&`, `||`, `!`, and referencing pointcuts across
        classes by fully-qualified method name.
1.13.12 Parameter binding: `args(account,..)`, `@annotation(auditable)`, `target(bean)`, and the
        `argNames` attribute when `-parameters` is unavailable. `[TRAP]`
1.13.13 Introductions: `@DeclareParents` / `DelegatingIntroductionInterceptor` — adding an interface
        to an existing bean. Rare but a real capability.
1.13.14 The low-level API for when annotations are not enough: `Pointcut`, `ClassFilter`,
        `MethodMatcher` (`matches(Method, Class)` and the 3-arg runtime form, `isRuntime()`),
        `Advisor`, `PointcutAdvisor`, `IntroductionAdvisor`,
        `DefaultPointcutAdvisor`, `NameMatchMethodPointcut`,
        `AnnotationMatchingPointcut`, `AspectJExpressionPointcut`,
        `ComposablePointcut`, `Pointcuts.union/intersection`. `[API]` `[SOURCE]`
1.13.15 The advice interfaces underneath the annotations: `org.aopalliance.intercept.MethodInterceptor`,
        `MethodBeforeAdvice`, `AfterReturningAdvice`, `ThrowsAdvice`, `IntroductionInterceptor`.
        Note that Spring implements the **AOP Alliance** interfaces, which is why the package is
        `org.aopalliance`. `[API]`
1.13.16 `ProxyFactory` / `ProxyFactoryBean` / `AdvisedSupport` / `Advised` — programmatic proxy
        creation, and the fact that `Advised` lets you inspect and mutate the advisor chain of any
        live proxy. `[API]`
1.13.17 `TargetSource` implementations: `SingletonTargetSource`, `HotSwappableTargetSource`,
        `CommonsPool2TargetSource`, `PrototypeTargetSource`, `ThreadLocalTargetSource`,
        `SimpleBeanTargetSource` (the scoped-proxy one). `[API]`
1.13.18 Auto-proxy creators: `AbstractAutoProxyCreator`, `AbstractAdvisorAutoProxyCreator`,
        `DefaultAdvisorAutoProxyCreator`, `BeanNameAutoProxyCreator`,
        `InfrastructureAdvisorAutoProxyCreator` (used by `@EnableTransactionManagement`),
        `AnnotationAwareAspectJAutoProxyCreator` (used by `@EnableAspectJAutoProxy`). `[API]`
1.13.19 One proxy, many advisors: multiple annotations on one bean produce **one** proxy with a
        sorted advisor chain, not nested proxies. `[TRAP]` `[PROVE]`
1.13.20 The default advisor order for the common annotations and how to change it
        (`@EnableTransactionManagement(order=...)`, `@EnableCaching(order=...)`,
        `@EnableAsync(order=...)`, `@Order` on your own aspect). Why cache-before-transaction and
        transaction-before-retry matter. `[TRAP]`
1.13.21 Spring AOP versus AspectJ: a comparison table over join points, weaving time, performance,
        self-invocation, build complexity, and what Spring itself uses.

*(21 leaves)*

## §1.14 `@Transactional` — the model

1.14.1 What the annotation actually is: metadata read by `AnnotationTransactionAttributeSource`
       into a `TransactionAttribute`, consumed by `TransactionInterceptor`. Nothing more.
1.14.2 The runtime mechanism in order: interceptor obtains a `PlatformTransactionManager` →
       `getTransaction(definition)` → manager acquires a `Connection`, calls
       `setAutoCommit(false)`, and **binds it to the thread** via
       `TransactionSynchronizationManager` → your method runs → commit or rollback → unbind.
       `[FLOW]` `[SOURCE]`
1.14.3 Why "the transaction is ambient": every `JdbcTemplate` / `EntityManager` call on that thread
       looks the connection up from the same `ThreadLocal`. `[PROVE]` `[X-REF 05]`
1.14.4 `PlatformTransactionManager` (`getTransaction`, `commit`, `rollback`) versus
       `ReactiveTransactionManager` versus `TransactionManager` marker. `[API]`
1.14.5 The implementations you meet: `DataSourceTransactionManager`,
       `JdbcTransactionManager` (the 5.3+ default in Boot for plain JDBC),
       `JpaTransactionManager`, `JtaTransactionManager`, `ChainedTransactionManager` (removed /
       discouraged), `R2dbcTransactionManager`. `[API]` `[VERSION-TRAP]` `[RESEARCH]`
1.14.6 `@Transactional` attribute surface in full: `value`/`transactionManager` (alias),
       `propagation`, `isolation`, `timeout`, `timeoutString`, `readOnly`, `rollbackFor`,
       `rollbackForClassName`, `noRollbackFor`, `noRollbackForClassName`, `label`. `[API]`
       `[RESEARCH]`
1.14.7 The seven `Propagation` values with a two-column table (existing tx / no tx):
       `REQUIRED`, `REQUIRES_NEW`, `SUPPORTS`, `NOT_SUPPORTED`, `MANDATORY`, `NEVER`, `NESTED`.
1.14.8 `REQUIRES_NEW` mechanics: the outer transaction is **suspended** (its resources unbound and
       stashed in a `SuspendedResourcesHolder`), a **second connection** is taken from the pool,
       and the inner transaction commits independently. `[SOURCE]` `[PROVE]`
1.14.9 The two consequences of that second connection: pool sizing doubles for that path, and the
       inner transaction can **self-deadlock** against rows locked by the suspended outer one.
       `[TRAP]` `[X-REF 09]`
1.14.10 `NESTED` mechanics: a JDBC **savepoint** in the *same* connection; inner rollback returns to
        the savepoint and the outer transaction survives. Requires
        `DataSourceTransactionManager` with `nestedTransactionAllowed = true`; **`JpaTransactionManager`
        supports it only with a JDBC-savepoint-capable setup**. `[TRAP]` `[RESEARCH]`
1.14.11 The five `Isolation` values (`DEFAULT`, `READ_UNCOMMITTED`, `READ_COMMITTED`,
        `REPEATABLE_READ`, `SERIALIZABLE`) mapping to `Connection.TRANSACTION_*` constants; the
        anomalies they prevent live in `09-sql-databases.md`. `[X-REF 09]`
1.14.12 **Trap:** `isolation` is ignored by `JpaTransactionManager` on some setups unless
        `entityManagerFactory` supports it — Hibernate historically threw
        `InvalidIsolationLevelException`. State the current behaviour. `[TRAP]` `[RESEARCH]`
1.14.13 The default rollback rule: rollback on `RuntimeException` and `Error`; **commit** on checked
        exceptions. Its origin is EJB CMT convention, not a technical constraint. `[TRAP]`
        `[PROVE]`
1.14.14 `rollbackFor = Exception.class` as the usual fix, and the "most specific rule wins" matching
        algorithm — `RollbackRuleAttribute` scores by class-hierarchy depth. `[SOURCE]`
        `[RESEARCH]`
1.14.15 `noRollbackFor` and the exact precedence between a `rollbackFor` and a `noRollbackFor` that
        both match. `[TRAP]`
1.14.16 `timeout` is in **seconds**, default `-1` (`TransactionDefinition.TIMEOUT_DEFAULT`), enforced
        by the transaction manager and pushed into statement timeouts where the manager supports it.
        `timeoutString` accepts a placeholder. `[NUM]` `[API]`
1.14.17 `readOnly = true` does three things: sets the JDBC connection read-only (drivers may reject
        writes or route to a replica), sets Hibernate's flush mode to `MANUAL` so **dirty checking
        is skipped**, and marks the transaction read-only for synchronizations. `[TRAP]`
        `[X-REF 08]`
1.14.18 `TransactionSynchronizationManager` API: `getResource`, `bindResource`, `unbindResource`,
        `isActualTransactionActive`, `isCurrentTransactionReadOnly`, `getCurrentTransactionName`,
        `registerSynchronization`. `[API]` `[SOURCE]`
1.14.19 `TransactionSynchronization` callbacks: `beforeCommit`, `beforeCompletion`, `afterCommit`,
        `afterCompletion(int status)` with `STATUS_COMMITTED = 0`, `STATUS_ROLLED_BACK = 1`,
        `STATUS_UNKNOWN = 2`. This is the machinery `@TransactionalEventListener` sits on.
        `[NUM]` `[API]`
1.14.20 `setRollbackOnly` and the `UnexpectedRollbackException` mechanism: an inner `REQUIRED`
        method marks the *shared* transaction rollback-only; the outer commit then throws
        `Transaction silently rolled back because it has been marked as rollback-only`. Show the
        message. `[TRAP]` `[DIAG]` `[PROVE]`
1.14.21 Programmatic transactions: `TransactionTemplate.execute` /
        `executeWithoutResult`, and `TransactionalOperator` for reactive. When explicit boundaries
        beat the annotation. `[API]`
1.14.22 `@EnableTransactionManagement(mode, proxyTargetClass, order)` and Boot's
        `TransactionAutoConfiguration` which enables it for you. `[API]`
1.14.23 Placement rules: annotate the **class or concrete method**, on the **service** layer, never
        an interface method (that only works with JDK proxies). `[TRAP]` `[X-REF 08]`
1.14.24 `@Transactional` on a `private`, `final`, or `static` method — compiles, does nothing, no
        warning. `[TRAP]`
1.14.25 `TransactionSystemException` on commit failure, and how a constraint violation surfaces at
        **flush/commit time** rather than at the offending statement. `[TRAP]` `[X-REF 08]`

*(25 leaves)*

## §1.15 Events

1.15.1 `ApplicationEventPublisher.publishEvent(Object)` — since Spring 4.2 any object works; it is
       wrapped in a `PayloadApplicationEvent` if it is not an `ApplicationEvent`. `[API]`
       `[VERSION-TRAP]`
1.15.2 `ApplicationEvent` base class, `getTimestamp()`, `getSource()`.
1.15.3 `ApplicationListener<E>` interface form vs `@EventListener` annotation form; the latter is
       wired by `EventListenerMethodProcessor` + `DefaultEventListenerFactory`. `[SOURCE]`
1.15.4 `@EventListener` attributes: `classes`/`value` (listen to several types),
       `condition` (SpEL). SpEL root variables available: `#root.event`, `#root.args`, `#argName`,
       `#a0`. `[API]` `[RESEARCH]`
1.15.5 A listener may **return** an event (or a collection of events) which is published in turn —
       chaining without an explicit publisher. `[API]` `[TRAP]`
1.15.6 Ordering listeners with `@Order`.
1.15.7 Generic events: `EntityCreatedEvent<Order>` resolves correctly only if the event implements
       `ResolvableTypeProvider` or the generic is statically known — erasure otherwise defeats
       matching. `[TRAP]` `[PROVE]` `[X-REF 06]`
1.15.8 **Plain `@EventListener` is synchronous, on the publisher's thread, inside the publisher's
       transaction.** An exception in the listener propagates to the publisher and rolls the
       transaction back. This surprises almost everyone. `[TRAP]` `[PROVE]`
1.15.9 `@TransactionalEventListener(phase = ...)` with `TransactionPhase` values
       `BEFORE_COMMIT`, `AFTER_COMMIT` (default), `AFTER_ROLLBACK`, `AFTER_COMPLETION`, plus
       `fallbackExecution` (default `false` — the listener is **skipped entirely** when there is no
       transaction). `[API]` `[NUM]` `[TRAP]`
1.15.10 Why `AFTER_COMMIT` is the correct place to send an email or publish to Kafka: it cannot
        notify about an order that then rolls back. `[PROVE]` `[X-REF 14]`
1.15.11 **Trap:** a database write inside an `AFTER_COMMIT` listener runs with **no** transaction
        (the outer one is already committed and the synchronization is in cleanup) — you need
        `@Transactional(propagation = REQUIRES_NEW)` on the listener. `[TRAP]`
1.15.12 `@Async @EventListener`: different thread, no transaction, no `ThreadLocal` context, and
        exceptions vanish into the executor's handler. `[TRAP]` `[X-REF 05]`
1.15.13 `ApplicationEventMulticaster` / `SimpleApplicationEventMulticaster`; setting a
        `taskExecutor` makes **all** events async, and `setErrorHandler` decides what happens to a
        thrown listener exception. Bean name `applicationEventMulticaster`. `[API]` `[SOURCE]`
1.15.14 The context's own event sequence: `ContextRefreshedEvent`, `ContextStartedEvent`,
        `ContextStoppedEvent`, `ContextClosedEvent`, plus `RequestHandledEvent` /
        `ServletRequestHandledEvent`. `[API]`
1.15.15 Spring Boot's application events in order: `ApplicationStartingEvent`,
        `ApplicationEnvironmentPreparedEvent`, `ApplicationContextInitializedEvent`,
        `ApplicationPreparedEvent`, `ContextRefreshedEvent`, `WebServerInitializedEvent`,
        `ApplicationStartedEvent`, `AvailabilityChangeEvent(LivenessState.CORRECT)`,
        `ApplicationReadyEvent`, `AvailabilityChangeEvent(ReadinessState.ACCEPTING_TRAFFIC)`,
        `ApplicationFailedEvent`. `[FLOW]` `[API]` `[RESEARCH]`
1.15.16 Events published **before** the context exists (`ApplicationStartingEvent`,
        `ApplicationEnvironmentPreparedEvent`) can only be observed by listeners registered in
        `spring.factories` or `SpringApplication.addListeners` — an `@EventListener` bean is too
        late. `[TRAP]` `[PROVE]`
1.15.17 `ContextRefreshedEvent` fires on **every** refresh, including a child servlet context —
        the classic "my startup code ran twice" bug. `[TRAP]`
1.15.18 `@EventListener` on a lazy bean is not registered — the reference doc warns about it
        explicitly. `[TRAP]` `[RESEARCH]`
1.15.19 When events are the wrong tool: they are in-process, unordered across listeners by default,
        and lost on crash. The durable version is an outbox plus a broker. `[X-REF 14]`

*(19 leaves)*

## §1.16 `Environment`, `PropertySource`, and profiles

1.16.1 `Environment` = profiles + properties. `PropertyResolver` methods: `getProperty`,
       `getProperty(key, default)`, `getRequiredProperty`, `containsProperty`,
       `resolvePlaceholders`, `resolveRequiredPlaceholders`. `[API]`
1.16.2 `ConfigurableEnvironment`: `getPropertySources()`, `setActiveProfiles`, `addActiveProfile`,
       `setDefaultProfiles`, `getSystemProperties`, `getSystemEnvironment`, `merge`. `[API]`
1.16.3 `PropertySource<T>` — name + backing source + `getProperty(String)`;
       `EnumerablePropertySource.getPropertyNames()`. `[API]`
1.16.4 `MutablePropertySources` ordering API: `addFirst`, `addLast`, `addBefore`, `addAfter`,
       `remove`, `replace`, `precedenceOf`. First in the list wins. `[API]` `[PROVE]`
1.16.5 `StandardEnvironment`'s two default sources and their exact names:
       `systemProperties` (`StandardEnvironment.SYSTEM_PROPERTIES_PROPERTY_SOURCE_NAME`) then
       `systemEnvironment` (`SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME`) — system properties win.
       `[NUM]` `[SOURCE]`
1.16.6 `StandardServletEnvironment` adds `servletConfigInitParams`, `servletContextInitParams`,
       `jndiProperties` ahead of those. `[RESEARCH]`
1.16.7 `@PropertySource` (repeatable) with `value`, `name`, `encoding`, `factory`,
       `ignoreResourceNotFound`; placeholders allowed in the location. **Does not support YAML**
       without a custom `PropertySourceFactory`. `[TRAP]` `[API]`
1.16.8 `PropertySourcesPlaceholderConfigurer`: `setIgnoreUnresolvablePlaceholders`,
       `setPlaceholderPrefix`/`Suffix`, `setValueSeparator`, `setNullValue`, and (6.2) the
       configurable **escape character**, backslash by default. `[API]` `[RESEARCH]`
       `[VERSION-TRAP]`
1.16.9 Placeholder syntax: `${key}`, `${key:default}`, nested `${a.${b}}`, and the failure
       `IllegalArgumentException: Could not resolve placeholder 'x' in value "${x}"`. `[DIAG]`
       `[TRAP]`
1.16.10 Profiles: `@Profile("dev")`, expression forms `!`, `&`, `|`, parentheses required when
        mixing `&` and `|`. `[API]` `[SOURCE]`
1.16.11 `spring.profiles.active`, `spring.profiles.default` (default value `default`),
        `spring.profiles.include`, `spring.profiles.group.<name>`. `[PROP]` `[RESEARCH]`
1.16.12 Boot 3.5 validates profile names: only letters, digits, `-`, `_` (and from 3.5.1 also `.`,
        `+`, `@`), not starting or ending with `-`/`_`; disable with
        `spring.profiles.validate=false`. `[PROP]` `[RESEARCH]` `[VERSION-TRAP]`
1.16.13 `@ActiveProfiles` in tests, and the fact that it is part of the context cache key
        (§3.22). `[X-REF 16]`
1.16.14 **Trap:** profiles as a place to keep secrets or environment URLs in git. Profiles select
        *behaviour* (stub vs real client); configuration belongs in the environment. `[TRAP]`
        `[X-REF 13]`
1.16.15 **Trap:** `@Profile` on a `@Configuration` class does not stop the class from being parsed
        if it is `@Import`ed directly — understand `ConfigurationPhase`. `[TRAP]`
1.16.16 Profile-conditional beans and AOT: profiles are largely resolved at **build time** under
        AOT/native, so profile-specific bean sets are a native-image limitation. `[X-REF §3.21]`
        `[RESEARCH]`

*(16 leaves)*

## §1.17 `@Value`, placeholders, and SpEL

1.17.1 `@Value("${...}")` (property placeholder) versus `@Value("#{...}")` (SpEL) — two different
       resolvers that people constantly conflate. `[TRAP]`
1.17.2 Resolution order for `@Value`: `PropertySourcesPlaceholderConfigurer` substitutes the
       placeholder text, then the `BeanExpressionResolver` evaluates SpEL, then the
       `ConversionService` converts to the target type. `[FLOW]` `[PROVE]`
1.17.3 `@Value` on a field is set **after** construction, so it is `null` inside the constructor and
       inside `@PostConstruct` only if injection ordering is misunderstood. Prefer constructor
       parameters. `[TRAP]`
1.17.4 `@Value` into a `List<String>` / `String[]` from a comma-separated property, and the
       `#{'${x}'.split(',')}` idiom. `[TRAP]`
1.17.5 SpEL API: `ExpressionParser`, `SpelExpressionParser`, `Expression.getValue`,
       `EvaluationContext`, `StandardEvaluationContext`, `SimpleEvaluationContext`,
       `ParserContext.TEMPLATE_EXPRESSION`. `[API]`
1.17.6 SpEL feature inventory: literals, property/array/list/map access, inline lists `{1,2}` and
       maps `{a:1}`, array construction, relational/logical/arithmetic operators, `matches` regex,
       method and constructor invocation, `T(java.lang.Math)` type references, variables `#var`,
       `#this`, `#root`, functions, bean references `@bean` and `&factoryBean`, ternary, Elvis
       `?:`, safe navigation `?.`, selection `?[...]`, projection `![...]`, expression templates.
       `[API]` `[RESEARCH]`
1.17.7 `SimpleEvaluationContext` versus `StandardEvaluationContext` as a **security** boundary —
       `StandardEvaluationContext` allows arbitrary type and constructor access, which is how SpEL
       injection RCEs happen. Never evaluate user input in a standard context. `[TRAP]`
       `[X-REF 13]`
1.17.8 `SpelCompilerMode` (`OFF`, `IMMEDIATE`, `MIXED`) and `spring.expression.compiler.mode`.
       `[API]` `[PROP]` `[RESEARCH]`
1.17.9 Where SpEL appears in the container: `@Value`, `@ConditionalOnExpression`,
       `@EventListener(condition=...)`, `@Cacheable(key=, condition=, unless=)`,
       `@PreAuthorize`/`@PostAuthorize`, `@Scheduled(cron="${...}")`, Spring Data `@Query` SpEL
       parameters. `[X-REF 13]` `[X-REF 15]`
1.17.10 `BeanExpressionResolver` / `StandardBeanExpressionResolver` and the `#{beanName.prop}`
        syntax inside bean definitions.
1.17.11 Cost: SpEL is reflective and interpreted by default. In a hot cache key this is measurable —
        prefer a `KeyGenerator`. `[PROVE]` `[X-REF 15]`

*(11 leaves)*

## §1.18 Type conversion, formatting, and validation

1.18.1 The legacy path: `java.beans.PropertyEditor`, `PropertyEditorRegistrar`,
       `CustomEditorConfigurer`, `@InitBinder`. Still the fallback when no `ConversionService` is
       registered. `[VERSION-TRAP]`
1.18.2 `Converter<S,T>`, `ConverterFactory<S,R>`, `GenericConverter` (+ `ConvertiblePair`),
       `ConditionalConverter`, `ConditionalGenericConverter`. `[API]`
1.18.3 `ConversionService` methods: `canConvert(Class,Class)`, `convert(Object, Class)`, and the
       `TypeDescriptor` overloads that preserve generics. `[API]`
1.18.4 `DefaultConversionService`, `DefaultFormattingConversionService`,
       `ConversionServiceFactoryBean`, `FormattingConversionServiceFactoryBean`.
       The container picks up a bean **named exactly `conversionService`**
       (`ConfigurableApplicationContext.CONVERSION_SERVICE_BEAN_NAME`). `[NUM]` `[TRAP]`
       `[SOURCE]`
1.18.5 `Formatter<T>` = `Printer<T>` + `Parser<T>`; `AnnotationFormatterFactory`;
       `@NumberFormat`, `@DateTimeFormat`, `@DurationUnit`, `@DataSizeUnit`. `[API]`
1.18.6 `TypeDescriptor` and how a `List<Integer>` → `List<String>` conversion is expressed.
1.18.7 Spring Boot's extra converters registered for configuration binding: `Duration`
       (ISO-8601 `PT1M` and simple `1m`), `Period` (`P30D`), `DataSize` (`10MB`), `InetAddress`,
       `Resource`, `Charset`, enums with relaxed matching. `[API]` `[RESEARCH]`
1.18.8 `@ConfigurationPropertiesBinding` to register a custom converter for binding only — and in
       Boot 3.5 such `@Bean` methods may be lambdas. `[API]` `[RESEARCH]` `[VERSION-TRAP]`
1.18.9 Bean Validation (Jakarta Validation 3.0) in the container: `LocalValidatorFactoryBean`,
       `MethodValidationPostProcessor`, `@Validated` (class-level, enables method validation),
       `@Valid` (cascade). `[API]`
1.18.10 The two different failure exceptions: `MethodArgumentNotValidException` (400) from
        `@Valid @RequestBody` on a controller, versus `ConstraintViolationException` from a
        `@Validated` service parameter. Different type, different handler. `[TRAP]`
        `[X-REF 12]`
1.18.11 `@Validated(Group.class)` validation groups, and why `@Valid` cannot express them.
1.18.12 `@Validated` on a bean makes it proxied — so it inherits every proxy limitation in §1.12.
        `[TRAP]` `[PROVE]`
1.18.13 Framework 6.1+ built-in method validation for controllers without a proxy
        (`HandlerMethodValidationException`), and how it changes the error shape. `[RESEARCH]`
        `[VERSION-TRAP]` `[X-REF 12]`
1.18.14 Spring's own `Validator` interface (`supports`, `validate`, `Errors`) versus Jakarta
        Validation, and `DataBinder`. `[API]`

*(14 leaves)*

## §1.19 Resources, `MessageSource`, and the small utilities

1.19.1 `Resource` interface: `exists`, `isReadable`, `isOpen`, `getURL`, `getFile`,
       `getInputStream`, `contentLength`, `lastModified`, `createRelative`, `getFilename`.
       `[API]`
1.19.2 Implementations: `ClassPathResource`, `FileSystemResource`, `UrlResource`,
       `ByteArrayResource`, `InputStreamResource`, `ServletContextResource`. `[API]`
1.19.3 Location prefixes: `classpath:`, `classpath*:`, `file:`, `http(s)://`, and none (context
       dependent). `classpath*:` scans **all** matching resources across the classpath. `[TRAP]`
1.19.4 `ResourceLoader` vs `ResourcePatternResolver`; `PathMatchingResourcePatternResolver` and
       Ant-style patterns.
1.19.5 **Trap:** `resource.getFile()` throws `FileNotFoundException` when the app runs from a fat
       jar — the resource is a jar entry, not a file. Use `getInputStream()`. `[TRAP]` `[DIAG]`
1.19.6 `@Value("classpath:schema.sql") Resource` injection.
1.19.7 `MessageSource` methods and the three implementations
       (`ResourceBundleMessageSource`, `ReloadableResourceBundleMessageSource`,
       `StaticMessageSource`); bean name **`messageSource`**; Boot's
       `spring.messages.basename` (default `messages`), `spring.messages.encoding`,
       `spring.messages.fallback-to-system-locale`. `[NUM]` `[PROP]` `[RESEARCH]`
1.19.8 `MessageSourceResolvable`, `NoSuchMessageException`, and how validation messages resolve
       through it.
1.19.9 `ApplicationStartup` / `StartupStep` and `BufferingApplicationStartup(int capacity)` /
       `FlightRecorderApplicationStartup` — the container's own tracing hooks, surfaced by the
       actuator `startup` endpoint. `[API]` `[X-REF 20]`

*(9 leaves)*

## §1.20 Spring Boot — what it actually is

1.20.1 Boot is four things and no more: auto-configuration, starters, embedded servers, and
       production-ready features (actuator). Say this before any mechanism.
1.20.2 `@SpringBootApplication` = `@SpringBootConfiguration` (itself `@Configuration`) +
       `@ComponentScan` (with `TypeExcludeFilter` and `AutoConfigurationExcludeFilter`) +
       `@EnableAutoConfiguration`. Its attributes: `exclude`, `excludeName`, `scanBasePackages`,
       `scanBasePackageClasses`, `nameGenerator`, `proxyBeanMethods`. `[API]` `[SOURCE]`
1.20.3 A **starter** is a dependency aggregator with essentially no code — `spring-boot-starter-web`
       is a POM that pulls in `spring-webmvc`, Jackson and embedded Tomcat. The auto-config lives
       in `spring-boot-autoconfigure`, gated on those classes appearing. `[PROVE]` `[TRAP]`
1.20.4 The starter inventory worth knowing by name: `web`, `webflux`, `data-jpa`, `data-redis`,
       `security`, `validation`, `actuator`, `test`, `aop`, `jdbc`, `batch`, `quartz`,
       `oauth2-client`, `oauth2-resource-server`, `amqp`, `cache`, `mail`, `thymeleaf`,
       `parent`. `[API]`
1.20.5 The Boot dependency-management BOM (`spring-boot-dependencies`) and why you should not pin
       library versions yourself. `[TRAP]`
1.20.6 `spring-boot-starter-parent` versus importing the BOM with `<scope>import</scope>`; what the
       parent adds beyond versions (`-parameters`, resource filtering, plugin config). `[TRAP]`
1.20.7 The fat jar layout: `BOOT-INF/classes`, `BOOT-INF/lib`, `org/springframework/boot/loader`,
       `META-INF/MANIFEST.MF` with `Main-Class: JarLauncher` and `Start-Class: your.Main`.
       `[SOURCE]` `[NUM]`
1.20.8 `JarLauncher` and the nested-jar classloader (`LaunchedClassLoader`); jars are stored
       **uncompressed** so they can be memory-mapped. `[X-REF 06]` `[RESEARCH]`
1.20.9 Layered jars (`layers.idx`: `dependencies`, `spring-boot-loader`,
       `snapshot-dependencies`, `application`) and why Docker layer caching wants them.
       `[X-REF 19]` `[RESEARCH]`
1.20.10 `spring-boot-maven-plugin` / `spring-boot-gradle-plugin` goals: `repackage`, `run`,
        `build-image` (Buildpacks/Paketo), `process-aot`, `build-info`. `[API]`
1.20.11 The actuator surface relevant to the container: `/actuator/beans`, `/actuator/conditions`,
        `/actuator/env`, `/actuator/configprops`, `/actuator/mappings`, `/actuator/startup`,
        `/actuator/health`, `/actuator/metrics`, `/actuator/threaddump`, `/actuator/heapdump`.
        In Boot 3.5 `heapdump` defaults to `access=NONE`. `[PROP]` `[RESEARCH]` `[X-REF 20]`
1.20.12 `management.endpoints.web.exposure.include` and why only `health` is exposed by default.
        `[PROP]` `[X-REF 13]`
1.20.13 What Boot is **not**: it is not a runtime, not an application server, and not a
        requirement — a plain `ApplicationContext` is still Spring. `[TRAP]`

*(13 leaves)*

## §1.21 Auto-configuration — the model

1.21.1 `@EnableAutoConfiguration` imports `AutoConfigurationImportSelector`, a
       `DeferredImportSelector` — hence auto-configuration is processed **after** all user
       configuration, which is what makes back-off work. `[PROVE]` `[SOURCE]`
1.21.2 The candidate list comes from every jar's
       `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — a
       plain newline-delimited list of class names, `#` for comments, `$` for nested classes.
       `[SOURCE]` `[NUM]`
1.21.3 Pre-2.7 this was the `EnableAutoConfiguration` key in `META-INF/spring.factories`;
       deprecated in 2.7, **removed in 3.0**. Any tutorial using `spring.factories` for
       auto-configuration is stale. `[VERSION-TRAP]` `[TRAP]`
1.21.4 `META-INF/spring/...AutoConfiguration.replacements` for renaming an auto-configuration
       without breaking `exclude`. `[RESEARCH]`
1.21.5 `@AutoConfiguration(before, after, beforeName, afterName)` — the 2.7+ replacement for
       `@Configuration` + `@AutoConfigureBefore`/`@AutoConfigureAfter`; it implies
       `proxyBeanMethods = false`. `[API]` `[VERSION-TRAP]` `[RESEARCH]`
1.21.6 `@AutoConfigureOrder`, `@AutoConfigureBefore`, `@AutoConfigureAfter` and the fact that
       ordering affects **condition evaluation order**, which is why `@ConditionalOnBean` is
       order-sensitive. `[PROVE]` `[TRAP]`
1.21.7 The full Boot condition inventory: `@ConditionalOnClass`, `@ConditionalOnMissingClass`,
       `@ConditionalOnBean`, `@ConditionalOnMissingBean`, `@ConditionalOnSingleCandidate`,
       `@ConditionalOnProperty`, `@ConditionalOnBooleanProperty`, `@ConditionalOnResource`,
       `@ConditionalOnWebApplication`, `@ConditionalOnNotWebApplication`,
       `@ConditionalOnWarDeployment`, `@ConditionalOnNotWarDeployment`,
       `@ConditionalOnExpression`, `@ConditionalOnJava`, `@ConditionalOnJndi`,
       `@ConditionalOnCloudPlatform`, `@ConditionalOnAvailableEndpoint`,
       `@ConditionalOnEnabledHealthIndicator`, `@ConditionalOnThreading`,
       `@ConditionalOnDefaultWebSecurity`. `[API]` `[RESEARCH]`
1.21.8 `@ConditionalOnProperty` attributes: `prefix`, `name`/`value`, `havingValue`,
       `matchIfMissing` (default `false`). The `matchIfMissing` semantics is the most-missed
       detail. `[NUM]` `[TRAP]`
1.21.9 `@ConditionalOnBooleanProperty` (Boot 3.4+) and Boot 3.5's stricter `.enabled` parsing —
       only `true`/`false` are accepted now, where previously any non-`false` value enabled.
       `[VERSION-TRAP]` `[RESEARCH]`
1.21.10 `@ConditionalOnProperty` and `@ConditionalOnBooleanProperty` became `@Repeatable` in Boot
        3.5. `[RESEARCH]` `[VERSION-TRAP]`
1.21.11 `@ConditionalOnMissingBean` attributes: `value`, `type`, `name`, `annotation`,
        `ignored`, `ignoredType`, `parameterizedContainer`, `search` (`SearchStrategy.ALL`,
        `CURRENT`, `ANCESTORS`). `[API]`
1.21.12 **Trap:** `@ConditionalOnBean`/`@ConditionalOnMissingBean` are only reliable **inside
        auto-configuration classes**, because their evaluation depends on definitions registered so
        far. In user configuration the result is order-dependent and effectively undefined.
        `[TRAP]` `[SOURCE]`
1.21.13 `@ConditionalOnMissingBean` matches by **return type of the `@Bean` method**, so declaring
        the return type as an interface can make the back-off miss. Declare the concrete type.
        `[TRAP]` `[RESEARCH]`
1.21.14 Excluding: `@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)`,
        `excludeName`, and `spring.autoconfigure.exclude`. Excluding a class that is not on the
        classpath throws unless you use `excludeName`. `[PROP]` `[TRAP]`
1.21.15 The **conditions evaluation report**: `--debug` or `-Ddebug=true` or
        `logging.level.org.springframework.boot.autoconfigure=DEBUG`, plus the
        `/actuator/conditions` endpoint. Read a real report: "Positive matches", "Negative matches"
        with reasons, "Exclusions", "Unconditional classes". This is the single best answer to
        "why isn't my `DataSource` created". `[DIAG]` `[PROP]`
1.21.16 Writing your own auto-configuration: the class, the `.imports` entry, the conditions, the
        `@ConfigurationProperties` companion, and the `spring-boot-autoconfigure-processor` that
        generates condition metadata for faster filtering. `[BUILD-ADJACENT]`
1.21.17 `AutoConfigurationMetadata` / `spring-autoconfigure-metadata.properties` as the
        *filtering* optimisation that avoids loading candidate classes whose
        `ConditionalOnClass` cannot match. `[RESEARCH]`
1.21.18 Testing auto-configuration with `ApplicationContextRunner`,
        `WebApplicationContextRunner`, `ReactiveWebApplicationContextRunner`,
        `withConfiguration(AutoConfigurations.of(...))`, `withPropertyValues`,
        `withUserConfiguration`, `withClassLoader(new FilteredClassLoader(X.class))`, and
        `ConditionEvaluationReportLoggingListener`. `[API]` `[X-REF 16]`
1.21.19 Boot 4.0 splits the monolithic `spring-boot-autoconfigure` jar into per-technology modules —
        an import-path change for anyone referencing auto-configuration classes by name.
        `[VERSION-TRAP]` `[RESEARCH]`

*(19 leaves)*

## §1.22 Externalized configuration and `@ConfigurationProperties`

1.22.1 The full Boot property-source precedence list, in order of **increasing** precedence:
       (1) default properties, (2) `@PropertySource` on `@Configuration`, (3) config data
       (`application.properties`/`.yaml`), (4) `RandomValuePropertySource`, (5) OS environment
       variables, (6) Java system properties, (7) JNDI `java:comp/env`, (8) `ServletContext` init
       params, (9) `ServletConfig` init params, (10) `SPRING_APPLICATION_JSON`, (11) command-line
       arguments, (12) `properties` on `@SpringBootTest`, (13) `@DynamicPropertySource`,
       (14) `@TestPropertySource`, (15) Devtools global settings. `[NUM]` `[SOURCE]` `[RESEARCH]`
1.22.2 The consequence that bites in production: an OS environment variable beats
       `application.yml`, and a stale env var silently overrides the config you just edited.
       `[TRAP]` `[X-REF 19]`
1.22.3 Config-data file search order: jar-internal `application.*`, jar-internal
       `application-{profile}.*`, external `application.*`, external `application-{profile}.*`;
       `.properties` beats `.yaml` in the same location. `[NUM]` `[TRAP]` `[RESEARCH]`
1.22.4 Default config locations: `classpath:/`, `classpath:/config/`, `file:./`, `file:./config/`,
       `file:./config/*/`. `[NUM]` `[RESEARCH]`
1.22.5 `spring.config.name` (default `application`), `spring.config.location`,
       `spring.config.additional-location`, `spring.config.import`,
       `spring.config.on-not-found=ignore`, and the `optional:` prefix. `[PROP]`
1.22.6 `spring.config.import` variants: file, `configtree:` (Kubernetes ConfigMap / Docker secrets
       at `/run/secrets/`), `env:VAR`, extension hints `[.yaml]`, `[encoding=utf-8]`, and
       fixed-versus-import-relative path resolution. `[PROP]` `[RESEARCH]`
1.22.7 Wildcard locations: exactly one `*`, must be the last path segment, sorted alphabetically by
       absolute path, not allowed in `classpath:`. `[NUM]` `[TRAP]` `[RESEARCH]`
1.22.8 Multi-document files: `---` in YAML, `#---` or `!---` in properties; per-document activation
       with `spring.config.activate.on-profile` and `spring.config.activate.on-cloud-platform`.
       Not supported by `@PropertySource`/`@TestPropertySource`. `[TRAP]` `[RESEARCH]`
1.22.9 `spring.config.activate.on-profile` replaced the deprecated `spring.profiles` document key
       in Boot 2.4 — and Boot 2.4 also changed config-data processing wholesale
       (`spring.config.use-legacy-processing`). This is a common source of stale advice.
       `[VERSION-TRAP]` `[RESEARCH]`
1.22.10 `SPRING_APPLICATION_JSON`, `spring.application.json`, and the rule that JSON `null` values
        are treated as missing. `[TRAP]` `[RESEARCH]`
1.22.11 `RandomValuePropertySource`: `${random.value}`, `${random.int}`, `${random.long}`,
        `${random.uuid}`, `${random.int(10)}`, `${random.int[1024,65536]}`. `[API]`
1.22.12 `@ConfigurationProperties(prefix)` binding modes: JavaBean (setters), constructor binding
        (immutable), and `record`. `[API]`
1.22.13 `@ConstructorBinding` placement changed in Boot 3.0: it now goes on the **constructor**, not
        the type, and is only needed when there is more than one constructor. `[VERSION-TRAP]`
        `[TRAP]`
1.22.14 Constructor binding requires `-parameters`; `@DefaultValue`; `@Name` for reserved keywords;
        and the rule that a nested type is `null` when entirely absent unless you use an empty
        `@DefaultValue`. `[TRAP]` `[RESEARCH]`
1.22.15 Enabling: `@EnableConfigurationProperties(X.class)`, `@ConfigurationPropertiesScan`, or
        `@Component` on the properties class. Generated bean name is
        `<prefix>-<fully.qualified.ClassName>`. `[NUM]` `[RESEARCH]`
1.22.16 `@ConfigurationProperties` on a `@Bean` method for binding third-party objects. `[API]`
1.22.17 Relaxed binding rules table: `my.person.first-name` (kebab, canonical),
        `my.person.firstName` (camel), `my.person.first_name` (underscore),
        `MY_PERSON_FIRSTNAME` (env var). Environment-variable rules: uppercase, `_` for `.`,
        remove other characters, `_` also matches nothing. `[NUM]` `[SOURCE]`
1.22.18 Relaxed binding applies to `@ConfigurationProperties` and **not** to `@Value` — the single
        strongest argument for the former. `[TRAP]` `[PROVE]`
1.22.19 Binding collections and maps: `list[0]`, YAML sequences, `map.key`, bracket notation for
        keys containing dots, and the fact that a `List` is **replaced** wholesale rather than
        merged across property sources. `[TRAP]`
1.22.20 Validation: `@Validated` on the properties class, JSR-303 constraints, failure at startup
        with a `BindValidationException` inside `ConfigurationPropertiesBindException`. Show the
        message. `[DIAG]` `[TRAP]`
1.22.21 `spring-boot-configuration-processor` generating
        `META-INF/spring-configuration-metadata.json` for IDE completion, and
        `additional-spring-configuration-metadata.json` for hand-written entries. `[API]`
1.22.22 `Binder` API for programmatic binding: `Binder.get(environment).bind("prefix",
        Bindable.of(X.class))`. `[API]`
1.22.23 `spring.config.import` + Vault/Consul/AWS Parameter Store as the production secret path,
        and why properties in a git-committed `application-prod.yml` is the anti-pattern.
        `[X-REF 13]`
1.22.24 `@Value` versus `@ConfigurationProperties` decision table: type safety, relaxed binding,
        SpEL support, validation, IDE metadata, grouping, testability. Only `@Value` supports SpEL;
        everything else favours `@ConfigurationProperties`. `[TRAP]`
1.22.25 Rebinding at runtime: `@RefreshScope` (Spring Cloud) and why plain Boot has no live reload.
        `[X-REF 18]`

*(25 leaves)*

## §1.23 Spring MVC — the request flow the container drives

1.23.1 The full pipeline, named at every arrow: servlet container → `Filter` chain →
       `DispatcherServlet.doDispatch` → `HandlerMapping` → `HandlerExecutionChain` →
       `HandlerInterceptor.preHandle` → `HandlerAdapter` → argument resolvers → controller method →
       return-value handler → `postHandle` → view resolution / message conversion →
       `afterCompletion` → back out through the filters. `[FLOW]`
1.23.2 The `DispatcherServlet` special bean types by exact name: `HandlerMapping`,
       `HandlerAdapter`, `HandlerExceptionResolver`, `ViewResolver`, `LocaleResolver` /
       `LocaleContextResolver`, `ThemeResolver` (removed in 6.0), `MultipartResolver`,
       `FlashMapManager`, `RequestToViewNameTranslator`. `[API]` `[VERSION-TRAP]` `[RESEARCH]`
1.23.3 `DispatcherServlet.properties` as the fallback defaults file when no bean of a type exists.
       `[SOURCE]`
1.23.4 `RequestMappingHandlerMapping` and `RequestMappingHandlerAdapter` as the pair that serve
       `@RequestMapping`; `SimpleUrlHandlerMapping` and `BeanNameUrlHandlerMapping` as the legacy
       pair.
1.23.5 `HandlerMethodArgumentResolver` inventory: `@RequestParam`, `@PathVariable`,
       `@RequestBody`, `@RequestHeader`, `@CookieValue`, `@ModelAttribute`, `@RequestPart`,
       `@MatrixVariable`, `@SessionAttribute`, `@RequestAttribute`, `Principal`,
       `HttpServletRequest`, `Errors`/`BindingResult`, `UriComponentsBuilder`. `[API]`
1.23.6 `HandlerMethodReturnValueHandler` and `HttpMessageConverter`:
       `MappingJackson2HttpMessageConverter`, `StringHttpMessageConverter`,
       `ByteArrayHttpMessageConverter`, `ResourceHttpMessageConverter`,
       `FormHttpMessageConverter`. Content negotiation via `ContentNegotiationManager`. `[API]`
       `[X-REF 12]`
1.23.7 `@RestController` = `@Controller` + `@ResponseBody` on every method.
1.23.8 The root vs servlet `WebApplicationContext` hierarchy in classic MVC, and the fact that
       Boot uses **one** context — which is why "my `@ControllerAdvice` isn't picked up because
       it's in the wrong context" is a legacy-only problem. `[VERSION-TRAP]`
1.23.9 Exception handling: `@ExceptionHandler` in a controller, `@ControllerAdvice` /
       `@RestControllerAdvice` globally, `ResponseEntityExceptionHandler` as the base class,
       `@ResponseStatus`, `ErrorResponse`/`ProblemDetail` (RFC 7807/9457) in Framework 6, and the
       `HandlerExceptionResolver` chain (`ExceptionHandlerExceptionResolver`,
       `ResponseStatusExceptionResolver`, `DefaultHandlerExceptionResolver`). `[API]`
       `[X-REF 12]`
1.23.10 Handler-method exception matching: most specific exception type wins; controller-local beats
        global; `@ControllerAdvice` can be scoped by `basePackages`, `assignableTypes`,
        `annotations`, and ordered with `@Order`. `[TRAP]`
1.23.11 **Trap:** returning a JPA entity from a controller — couples the API to the schema, triggers
        lazy loads mid-serialization (`LazyInitializationException` after the status line is
        already flushed), and leaks fields. Return a record DTO. `[TRAP]` `[X-REF 08]`
        `[X-REF 12]`
1.23.12 `@Valid @RequestBody` → `MethodArgumentNotValidException` → 400; the difference from
        `ConstraintViolationException` (§1.18.10); `@Valid` on a nested field for cascade.
1.23.13 Filter vs `HandlerInterceptor` vs AOP aspect — the four-row comparison table (layer, what it
        sees, what it can do, what to use it for), and the nesting order (filters outermost, then
        interceptors, then aspects).
1.23.14 `FilterRegistrationBean` for ordering and URL-scoping a filter, `@Order` /
        `OrderedFilter`, and `OncePerRequestFilter` as the base class that prevents double
        execution on `FORWARD`/`ASYNC` dispatches. `[API]` `[TRAP]`
1.23.15 Spring Security is a **filter chain** (`DelegatingFilterProxy` →
        `FilterChainProxy`) — which is why a 401/403 never reaches your `@ControllerAdvice` by
        default. `[TRAP]` `[X-REF 13]`
1.23.16 Async MVC: returning `Callable`, `DeferredResult`, `CompletableFuture`,
        `StreamingResponseBody`, `SseEmitter`; the request is released from the container thread
        and `afterCompletion` behaves differently. `[X-REF 05]`
1.23.17 `RequestContextHolder`, `ServletRequestAttributes`, and how request-scoped beans and
        `@RequestScope` hang off it (§1.8.11).
1.23.18 Boot's embedded-server auto-configuration: `ServletWebServerFactoryAutoConfiguration`,
        `TomcatServletWebServerFactory`, `WebServerFactoryCustomizer`,
        `server.*` properties (`server.port`, `server.servlet.context-path`,
        `server.tomcat.threads.max` default **200**, `server.tomcat.accept-count` default **100**,
        `server.tomcat.max-connections` default **8192**). `[PROP]` `[NUM]` `[RESEARCH]`
        `[X-REF 10]`
1.23.19 `WebMvcAutoConfiguration` versus `@EnableWebMvc` — adding `@EnableWebMvc` **switches off**
        Boot's MVC auto-configuration entirely. The classic self-inflicted outage.
        `[TRAP]` `[PROVE]`
1.23.20 `WebMvcConfigurer` as the supported customisation hook (`addInterceptors`,
        `addCorsMappings`, `addResourceHandlers`, `configureMessageConverters`,
        `addArgumentResolvers`, `addFormatters`). `[API]`

*(20 leaves)*

## §1.24 Scheduling and `@Async`

1.24.1 `@EnableScheduling`, `ScheduledAnnotationBeanPostProcessor`, `TaskScheduler`,
       `ThreadPoolTaskScheduler`, `ScheduledTaskRegistrar`, `SchedulingConfigurer`. `[API]`
1.24.2 `@Scheduled` attributes: `cron`, `zone`, `fixedDelay`, `fixedDelayString`, `fixedRate`,
       `fixedRateString`, `initialDelay`, `initialDelayString`, `timeUnit`, `scheduler`
       (6.1+). `[API]` `[RESEARCH]`
1.24.3 The Spring cron expression has **six** fields (second minute hour day-of-month month
       day-of-week), not Unix's five. `@Scheduled(cron = "0 0 3 * * *")` = 03:00 daily.
       Macros: `@yearly`, `@monthly`, `@weekly`, `@daily`, `@hourly`. `[NUM]` `[TRAP]`
1.24.4 `fixedDelay` measures from the **end** of the previous run; `fixedRate` from the **start**,
       so a slow run causes catch-up bursts. `[PROVE]` `[TRAP]`
1.24.5 **Trap:** the default scheduler has **one** thread. Two `@Scheduled` methods, or one slow
       job, and everything queues. Fix: `spring.task.scheduling.pool.size` (default **1**) or a
       `ThreadPoolTaskScheduler` bean. `[PROP]` `[NUM]` `[TRAP]`
1.24.6 **Trap:** every replica runs the job. Three pods, three executions. Fixes ranked: ShedLock
       (DB lock row), leader election, an external scheduler (Kubernetes `CronJob`, EventBridge)
       hitting one endpoint, or a queue with a single consumer. `[TRAP]` `[X-REF 19]`
       `[X-REF 14]`
1.24.7 A `@Scheduled` method must be no-arg and return `void`; it may be `@Transactional` (via the
       proxy), and it runs with **no** request context and no security context. `[TRAP]`
1.24.8 An unhandled exception from a `@Scheduled` method: for `cron`/`fixedDelay` the next run still
       happens, but state that precisely and show the logged handler. `[TRAP]` `[RESEARCH]`
1.24.9 `spring.task.scheduling.*` and `spring.task.execution.*` property surface:
       `pool.size`, `pool.core-size` (default **8**), `pool.max-size`,
       `pool.queue-capacity` (default `Integer.MAX_VALUE`), `pool.keep-alive`,
       `thread-name-prefix`, `shutdown.await-termination`,
       `shutdown.await-termination-period`. `[PROP]` `[NUM]` `[RESEARCH]` `[X-REF 05]`
1.24.10 `@EnableAsync(mode, proxyTargetClass, annotation, order)`,
        `AsyncAnnotationBeanPostProcessor`, `AsyncExecutionInterceptor`. `[API]`
1.24.11 `@Async` return types: `void` (fire and forget), `Future<T>`, `CompletableFuture<T>`,
        `ListenableFuture` (deprecated in 6.0). `[API]` `[VERSION-TRAP]`
1.24.12 **Trap:** a `void` `@Async` method **swallows** exceptions. Register an
        `AsyncUncaughtExceptionHandler` via `AsyncConfigurer.getAsyncUncaughtExceptionHandler()`,
        or return a `CompletableFuture`. `[TRAP]`
1.24.13 The default executor: Boot auto-configures `applicationTaskExecutor`
        (a `ThreadPoolTaskExecutor`, or a `SimpleAsyncTaskExecutor` with virtual threads when
        `spring.threads.virtual.enabled=true`). Boot 3.5 **removed** the `taskExecutor` alias —
        only `applicationTaskExecutor` remains. `[VERSION-TRAP]` `[RESEARCH]` `[TRAP]`
1.24.14 `spring.task.execution.mode=force` (Boot 3.5) to make Boot still auto-configure the
        `AsyncTaskExecutor` when you define your own `Executor`. `[PROP]` `[RESEARCH]`
1.24.15 **Trap:** an unbounded `queue-capacity` means `max-size` is never reached; the pool never
        grows and work piles in memory. `[TRAP]` `[X-REF 05]`
1.24.16 Context propagation into `@Async`: `TaskDecorator`,
        `DelegatingSecurityContextAsyncTaskExecutor`, an MDC-copying decorator, and
        `io.micrometer:context-propagation`. Nothing propagates by default. `[TRAP]`
        `[X-REF 05]` `[X-REF 20]`
1.24.17 `@Async` goes through the proxy, so **every** §1.12 limitation applies: self-invocation,
        `private`/`final`, and `@PostConstruct`. `[TRAP]`
1.24.18 `spring.main.keep-alive=true` — with virtual threads and no non-daemon thread, the JVM can
        exit before your `@Scheduled` job ever runs. `[PROP]` `[TRAP]` `[RESEARCH]`
1.24.19 Quartz (`spring-boot-starter-quartz`) as the durable, clustered alternative, and when to
        reach for it instead of `@Scheduled`.

*(19 leaves)*

## §1.25 The cache abstraction

1.25.1 `Cache` and `CacheManager` interfaces; `@EnableCaching(mode, proxyTargetClass, order)`;
       `CacheInterceptor` as the advice. `[API]` `[X-REF 15]`
1.25.2 `@Cacheable` attributes: `value`/`cacheNames`, `key`, `keyGenerator`, `cacheManager`,
       `cacheResolver`, `condition`, `unless`, `sync`. `[API]`
1.25.3 `condition` is evaluated **before** the method, `unless` **after** (and can see `#result`).
       `[TRAP]` `[PROVE]`
1.25.4 `@CachePut` (always executes, always writes), `@CacheEvict` (`allEntries`,
       `beforeInvocation`), `@Caching` (compose several), `@CacheConfig` (class-level defaults).
       `[API]`
1.25.5 `SimpleKeyGenerator` / `SimpleKey`: no params → `SimpleKey.EMPTY`; one param → the param
       itself; several → a `SimpleKey` of all of them. Two methods in the same cache with the same
       single argument therefore **collide**. `[TRAP]` `[NUM]` `[PROVE]`
1.25.6 `sync = true` prevents the thundering herd for one key on one node — and is not supported by
       every `CacheManager`. `[X-REF 15]`
1.25.7 `null` caching: `ConcurrentMapCacheManager` and `CaffeineCacheManager` cache `null` by
       default via `NullValue`; Redis needs `disableCachingNullValues` reasoning. `[TRAP]`
1.25.8 JSR-107 annotations (`@CacheResult`, `@CachePut`, `@CacheRemove`, `@CacheRemoveAll`) and how
       they differ from Spring's.
1.25.9 Boot's `CacheAutoConfiguration`, `spring.cache.type`
       (`simple`, `caffeine`, `redis`, `jcache`, `none`), `spring.cache.cache-names`. `[PROP]`
       `[X-REF 15]`
1.25.10 `@Cacheable` obeys every proxy rule: self-invocation silently skips the cache, `private`
        methods are never cached. `[TRAP]`

*(10 leaves)*

---

**PART 1 total: 11+13+15+18+10+22+14+19+18+17+13+16+21+25+19+16+11+14+9+13+19+25+20+19+10 = 397 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master cost table** — every container operation with its cost and when it is paid:
      definition registration (startup, O(definitions)), component scan (startup, O(classes on
      scanned packages), ASM parse per class), singleton instantiation (startup, O(graph)),
      `getBean` by name (runtime, O(1) map lookup), `getBean` by type (runtime, cached after first
      resolution), prototype creation (per call, full creation path), proxy creation (once per
      bean at `postProcessAfterInitialization`), proxied method call (per call, chain length),
      scoped-proxy call (per call, plus a `Scope.get`), SpEL evaluation (per call unless compiled),
      property placeholder resolution (once at definition time for `${}` in definitions, per
      binding for `@Value`), event publication (O(listeners), synchronous), transaction begin
      (one pool checkout + `setAutoCommit`), transaction commit/rollback (one round trip).
      Amortised versus worst case split out for the by-type lookups and the pool checkout.
2.1.2 **The proxy decision table**: JDK vs CGLIB vs AspectJ LTW vs AspectJ CTW vs no proxy, across
      requires-interface, advises-self-invocation, advises-private, advises-final, advises-fields,
      build complexity, startup cost, per-call cost.
2.1.3 **The injection-style table**: constructor vs setter vs field vs `ObjectProvider` vs
      `@Lookup`, across immutability, testability, cycle behaviour, optionality, laziness.
2.1.4 **The scope table**: instances-per, destruction-callback, proxy-needed-when-injected-into,
      thread-binding mechanism, typical bug.
2.1.5 **The propagation table** (existing tx / no tx / connections used / rollback interaction /
      typical use).
2.1.6 **The annotation-vs-mechanism table**: for each of `@Transactional`, `@Cacheable`, `@Async`,
      `@Retryable`, `@PreAuthorize`, `@Validated`, `@Observed` — which post-processor creates the
      proxy, which advisor, default order, and what silently breaks.
2.1.7 **The lifecycle-phase table**: for each phase, what exists yet, what can be injected, and
      which mistakes are possible there.
2.1.8 **The property-precedence table** with a concrete worked example resolving one key through
      all fifteen sources.
2.1.9 **The exception table**: `NoSuchBeanDefinitionException`,
      `NoUniqueBeanDefinitionException`, `UnsatisfiedDependencyException`,
      `BeanCurrentlyInCreationException`, `BeanCreationException`,
      `BeanDefinitionOverrideException`, `BeanInstantiationException`,
      `BeanNotOfRequiredTypeException`, `ApplicationContextException`,
      `ConfigurationPropertiesBindException`, `UnexpectedRollbackException`,
      `TransactionSystemException`, `IllegalStateException: No thread-bound request found`,
      `AopConfigException` — each with cause and first diagnostic step. `[DIAG]`

*(9 leaves)*

## §2.2 Wiring decisions — which one and why

2.2.1 Constructor injection as the default, with the two genuine exceptions (optional
      reconfigurable dependency → setter; circular design you cannot yet fix → `@Lazy` + setter).
2.2.2 When to inject a `List<T>` strategy set versus a `Map<String,T>` registry versus an explicit
      `switch` over a sealed interface. `[X-REF 04]`
2.2.3 When `ObjectProvider` earns its complexity: optional collaborator, prototype-per-call, and
      breaking an initialisation cycle without `@Lazy`.
2.2.4 When to use a `FactoryBean` versus a `@Bean` method versus a `@Configuration` with
      `@Conditional`.
2.2.5 When `@Qualifier` beats `@Primary`: `@Primary` is a global default and hides the second
      candidate at every injection point; `@Qualifier` is local and explicit.
2.2.6 Custom qualifier annotations as the type-safe replacement for stringly-typed names, and the
      refactoring-safety argument. `[PROVE]`
2.2.7 Interface-per-implementation as a reflex: when the interface is real abstraction and when it
      is `XService`/`XServiceImpl` ceremony that buys nothing. `[TRAP]`
2.2.8 Composition root discipline: keep `@Configuration` classes thin and cohesive, never scan the
      whole world, and prefer explicit `@Import` in libraries.
2.2.9 Number of dependencies as a design signal — the constructor-parameter count as a
      free SRP metric.
2.2.10 Bean count and startup time: measure it (`/actuator/beans`, `ApplicationStartup`) before
       optimising. `[X-REF 20]`

*(10 leaves)*

## §2.3 Lifetime mismatch and scoped proxies in practice

2.3.1 The general rule: injecting a **shorter**-lived bean into a **longer**-lived one requires
      indirection; the reverse never does. `[PROVE]`
2.3.2 The four indirection tools compared: scoped proxy, `ObjectProvider`, `@Lookup`,
      `ApplicationContext.getBean`.
2.3.3 Why a scoped proxy needs `TARGET_CLASS` in a Boot app (no interface guarantee), and what
      `INTERFACES` buys when there is one.
2.3.4 A request-scoped `CurrentUser` holder injected into a singleton service — the canonical
      worked example, with the thread-binding trace.
2.3.5 The same holder accessed from `@Async` or `@Scheduled` → `No thread-bound request found`,
      and the correct fix (pass the value as a parameter, do not smuggle it in scope).
      `[TRAP]`
2.3.6 Prototype beans that hold resources: nobody calls `@PreDestroy`, so a prototype holding a
      socket or a file handle leaks. Manage it yourself or do not make it a bean. `[TRAP]`
2.3.7 A custom `tenant` scope backed by a `ThreadLocal` or the security context, with a worked
      `Scope` implementation sketch. `[X-REF §4.x]`
2.3.8 `SimpleThreadScope` does **not** run destruction callbacks on thread death — a documented
      leak surface. `[TRAP]` `[RESEARCH]` `[X-REF 05]`

*(8 leaves)*

## §2.4 What can and cannot be advised — a checklist

2.4.1 The five-question checklist you run when an annotation "doesn't work": is the class a bean?
      is the call coming in through the proxy? is the method public and non-final? is the enabling
      `@Enable*`/auto-configuration active? is the annotation on a class the proxy actually
      advises? `[FLOW]`
2.4.2 Verifying at runtime: log `AopUtils.isAopProxy(bean)`, `getClass().getName()` containing
      `$$SpringCGLIB$$` (6.0+) or `$$EnhancerBySpringCGLIB$$` (5.x), and
      `((Advised) bean).getAdvisors()`. `[DIAG]` `[VERSION-TRAP]`
2.4.3 `final` class → `Cannot subclass final class`; the exact stack, and the two fixes (drop
      `final`, or extract an interface and let JDK proxies run).
2.4.4 `private` method → no error, no advice. `protected`/package-private → advised by CGLIB only if
      the proxy is in the same package.
2.4.5 `static` method → never advised, because there is nothing to override.
2.4.6 Calling an advised method on a field of your own class that you assigned with `new` — you
      never got the bean at all. `[TRAP]`
2.4.7 A `@Component` created by another `@Component` with `new` is not a bean; nothing is advised
      and nothing is injected. `[TRAP]`
2.4.8 Advising a bean created inside a `BeanPostProcessor`'s dependency graph (§1.10.12), with the
      exact Boot log line to grep for. `[DIAG]`
2.4.9 Advising `default` interface methods, records, and sealed types under CGLIB — records are
      `final`, so a record can never be a CGLIB-proxied bean. `[TRAP]` `[X-REF 04]`
2.4.10 Ordering multiple advisors on one bean: cache outside transaction (so a cache hit never
       opens a transaction), transaction inside retry (so each attempt is its own transaction) —
       and how to actually set the orders. `[PROVE]` `[TRAP]`

*(10 leaves)*

## §2.5 Self-invocation — the bypass, and the ranked fixes

2.5.1 The mechanism restated as a proof: the proxy delegates to the target; inside the target
      `this` is the target; a `this.m()` call is a plain `invokevirtual` on the target; the
      interceptor chain is never entered. `[PROVE]` `[X-REF 06]`
2.5.2 The three annotations it silently breaks and the distinct symptom of each:
      `@Transactional` (no transaction, partial writes committed statement-by-statement),
      `@Cacheable` (cache never consulted, load spike), `@Async` (runs synchronously on the caller
      thread, latency regression).
2.5.3 The five ranked fixes: (1) move the method to a **different bean** and inject it — cleanest,
      makes the boundary a visible collaboration; (2) self-inject the proxy
      (`@Autowired @Lazy private InvoiceService self;`) — works, is a smell; (3)
      `AopContext.currentProxy()` with `exposeProxy = true` — ties code to Spring;
      (4) programmatic `TransactionTemplate` / `CacheManager` — best when you wanted fine-grained
      boundaries anyway; (5) AspectJ weaving — a real fix, rarely worth the build cost.
2.5.4 Why `@Lazy` is needed on the self-injection: without it the bean depends on itself during
      creation and you get `BeanCurrentlyInCreationException`. `[PROVE]`
2.5.5 `ObjectProvider<Self>` as a fourth spelling of self-injection that avoids `@Lazy`.
2.5.6 How to spot it in code review, mechanically: grep for `this.` immediately preceding a method
      that carries a proxy annotation, and for `private` + `@Transactional`/`@Async`/`@Cacheable`.
2.5.7 An ArchUnit rule or a custom `BeanPostProcessor` that fails the build when a `private` or
      `final` method carries a proxy annotation. `[X-REF 16]`
2.5.8 The same bypass in `@Configuration` lite mode: an inter-`@Bean` call with
      `proxyBeanMethods = false` creates a second instance, so two beans hold different objects.
      `[TRAP]` `[PROVE]`

*(8 leaves)*

## §2.6 Transaction propagation in practice

2.6.1 The "audit row must survive a business rollback" problem, solved four ways:
      `REQUIRES_NEW`, an `AFTER_COMPLETION` event listener, an outbox row written in the same
      transaction and drained later, or an append to a log outside the DB. Compare them on
      atomicity, pool cost, and deadlock risk. `[X-REF 14]`
2.6.2 The `REQUIRES_NEW` pool-exhaustion arithmetic: with pool size N and every request taking two
      connections, throughput halves and at N/2 concurrent requests the pool deadlocks. Show the
      numbers. `[PROVE]` `[NUM]` `[X-REF 09]`
2.6.3 `NESTED` versus `REQUIRES_NEW`: savepoint in one connection versus an independent
      transaction; what the outer rollback can and cannot undo in each case. `[PROVE]`
2.6.4 `MANDATORY` as a design assertion — "this repository method must never run outside a
      transaction" — and where it is worth the coupling.
2.6.5 `NOT_SUPPORTED` for a long read that should not hold a transaction open, and `NEVER` as a
      guard against accidental enrolment.
2.6.6 Nesting behaviour matrix: outer `REQUIRED` + inner `REQUIRED`, + inner `REQUIRES_NEW`,
      + inner `NESTED`, + inner `NOT_SUPPORTED`, with the commit/rollback outcome of each.
2.6.7 The rollback-only contagion rule: with `REQUIRED`, the inner method shares the physical
      transaction, so any inner rollback poisons the whole thing regardless of whether the outer
      caught the exception. `[PROVE]` `[TRAP]`
2.6.8 Transaction boundaries and the unit of work: one transaction per business operation, opened
      at the service layer, never spanning an external HTTP call. `[TRAP]` `[X-REF 10]`
2.6.9 Long transactions as an availability problem: locks held, connections held, replication lag,
      and vacuum/undo growth. `[X-REF 09]`
2.6.10 Testing propagation: `@Transactional` on a test rolls back by default
       (`@Rollback(false)`/`@Commit` to change it), and that default makes `REQUIRES_NEW`
       behaviour in tests different from production. `[TRAP]` `[X-REF 16]`
2.6.11 Distributed transactions: why XA/`JtaTransactionManager` is almost always the wrong answer
       now, and what replaces it (outbox, saga, idempotent consumers). `[X-REF 14]`
2.6.12 `TransactionTemplate` for fine-grained boundaries inside a long method, and the
       `TransactionOperations.withoutTransaction()` no-op for tests. `[API]`
2.6.13 Multiple transaction managers: naming them and selecting with
       `@Transactional("secondaryTxManager")`; the failure when you have two and no `@Primary`.
       `[TRAP]`

*(13 leaves)*

## §2.7 Rollback rules in practice

2.7.1 The default rule restated with the historical reason (EJB CMT), and the argument that it is
      surprising rather than wrong. `[PROVE]`
2.7.2 The team-level fix: a composed `@BusinessTransactional` meta-annotation carrying
      `rollbackFor = Exception.class`, applied everywhere. `[X-REF §1.5.7]`
2.7.3 Catch-and-swallow inside a `REQUIRED` inner call → `UnexpectedRollbackException` at the outer
      commit. Full trace and the three fixes (do not swallow; use `REQUIRES_NEW`; move the
      try/catch outside the transaction). `[TRAP]` `[DIAG]`
2.7.4 Catch-and-continue **inside the same** transactional method: the transaction is not marked
      rollback-only by the interceptor (it never saw the exception), so partial work commits. The
      mirror-image bug of 2.7.3. `[TRAP]` `[PROVE]`
2.7.5 `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()` when you must roll
      back without throwing.
2.7.6 Exceptions thrown at **commit** time (constraint violations flushed late) cannot be caught
      inside the method — they surface at the proxy boundary. `[TRAP]` `[X-REF 08]`
2.7.7 `rollbackFor` on a checked exception whose subclass is also listed in `noRollbackFor` —
      resolve it with the depth-scoring rule. `[PROVE]`
2.7.8 The interaction with `@Retryable`: retrying outside the transaction retries the whole unit;
      retrying inside a rolled-back transaction is useless. Order matters. `[TRAP]`

*(8 leaves)*

## §2.8 Events in practice

2.8.1 A decision table: direct method call vs `@EventListener` vs `@TransactionalEventListener` vs
      an outbox + broker, across coupling, atomicity, durability, ordering, and testability.
      `[X-REF 14]`
2.8.2 The "send the confirmation email" worked example, done wrong four ways and right once.
2.8.3 Making a listener idempotent, because `AFTER_COMMIT` plus a crash means the notification may
      never be sent — events are not durable. `[PROVE]` `[X-REF 14]`
2.8.4 Ordering across listeners with `@Order`, and why relying on it is fragile.
2.8.5 Error handling: `SimpleApplicationEventMulticaster.setErrorHandler`, and the difference
      between failing the publisher and logging.
2.8.6 Async events done properly: a dedicated bounded executor, a `TaskDecorator` for MDC and
      security context, and an explicit exception handler. `[X-REF 05]` `[X-REF 20]`
2.8.7 Testing events: `@RecordApplicationEvents` + `ApplicationEvents` (Framework 5.3.3+), and
      `ApplicationEventPublisher` as a mock. `[API]` `[X-REF 16]`
2.8.8 Events as an in-process decoupling tool inside a modular monolith (Spring Modulith's
      `@ApplicationModuleListener` = `@Async` + `@TransactionalEventListener` + `@Transactional`
      + an event publication registry for durability). `[RESEARCH]`

*(8 leaves)*

## §2.9 Auto-configuration in practice

2.9.1 The diagnosis procedure for "bean X was/wasn't created": run with `--debug`, read the
      conditions report, find X's auto-configuration, read the *reason* string, act. `[FLOW]`
      `[DIAG]`
2.9.2 The five most common reasons in that report and what each means: `@ConditionalOnClass did not
      find required class`, `@ConditionalOnMissingBean found beans of type`, `@ConditionalOnProperty
      (x.y) did not find property`, `@ConditionalOnBean did not find any beans`, `Ancestor
      org.x.YAutoConfiguration did not match`. `[DIAG]` `[RESEARCH]`
2.9.3 Overriding an auto-configured bean correctly: define your own of the same type and let
      `@ConditionalOnMissingBean` back off — and the failure mode when the auto-config's condition
      is on a *different* type than yours.
2.9.4 Customising instead of replacing: `WebServerFactoryCustomizer`,
      `Jackson2ObjectMapperBuilderCustomizer`, `RestClientCustomizer`,
      `HibernatePropertiesCustomizer`, `WebMvcConfigurer`, `SecurityFilterChain` beans.
      The `*Customizer` idiom is the intended extension point. `[API]`
2.9.5 When to exclude an auto-configuration and when excluding is a smell.
2.9.6 Writing a company starter: the `-spring-boot-starter` naming convention, the autoconfigure
      module split, the `.imports` file, conditions, `@ConfigurationProperties`, metadata,
      and tests with `ApplicationContextRunner`.
2.9.7 The startup-time cost of auto-configuration and how to measure it
      (`/actuator/startup`, `BufferingApplicationStartup`, `spring.main.lazy-initialization`,
      AOT). `[X-REF 20]`
2.9.8 `@TestConfiguration` vs `@Configuration` inside a test, and `@ImportAutoConfiguration` for
      slice tests. `[X-REF 16]`

*(8 leaves)*

## §2.10 Configuration in practice

2.10.1 A configuration layering strategy for one service across local / CI / staging / prod, using
       profiles for behaviour and environment variables for values. `[X-REF 19]`
2.10.2 The twelve-factor argument, and where Spring deviates from it.
2.10.3 Secrets: never in `application*.yml` in git; `spring.config.import=configtree:/run/secrets/`,
       Kubernetes secrets mounted as files, Vault, AWS Parameter Store. `[X-REF 13]`
       `[X-REF 18]`
2.10.4 Fail fast on missing configuration: no `@Value` defaults for things that must be set,
       `@Validated` `@ConfigurationProperties` with `@NotBlank`, and a startup assertion bean.
       `[PROVE]`
2.10.5 Debugging a property: `/actuator/env` shows the winning source and the shadowed ones;
       `/actuator/configprops` shows what actually bound. `[DIAG]` `[X-REF 20]`
2.10.6 The relaxed-binding gotcha in Kubernetes: a `MY_APP_URL` env var binds to `my.app.url` for
       `@ConfigurationProperties` but not for `@Value("${my.app.url}")` on some spellings — state
       exactly when each works. `[TRAP]` `[RESEARCH]`
2.10.7 Property placeholders inside `application.yml` referring to other keys, and the escaping
       rules (6.2's backslash escape). `[RESEARCH]`
2.10.8 Migrating `@Value` fields to a `record` `@ConfigurationProperties` — a mechanical recipe.
2.10.9 Config that must change without a restart: why Boot has none natively, and the three real
       options (Spring Cloud Config + `@RefreshScope`, a database-backed settings bean, a feature
       flag service). `[X-REF 18]`

*(9 leaves)*

## §2.11 Startup, shutdown and the container's runtime behaviour

2.11.1 The startup budget decomposed: JVM start, classpath scan, condition evaluation, bean
       instantiation, embedded server start, and where each is measured. `[X-REF 06]`
2.11.2 The levers, ranked by payoff: fewer scanned packages, `spring.main.lazy-initialization`,
       excluding unused auto-configuration, CDS/AppCDS, Spring AOT, `@Bean(bootstrap=BACKGROUND)`,
       GraalVM native image. State the honest numbers for each. `[NUM]` `[X-REF 06]`
2.11.3 The lazy-initialization trade: faster startup, but the first request pays and configuration
       errors surface late — never enable it in production without a warmup request. `[TRAP]`
2.11.4 Readiness versus liveness: `ApplicationAvailability`, `AvailabilityChangeEvent`,
       `LivenessState`, `ReadinessState`, `/actuator/health/liveness`, `/actuator/health/readiness`,
       `management.endpoint.health.probes.enabled`. `[PROP]` `[X-REF 19]`
2.11.5 Graceful shutdown end to end: `SIGTERM` → shutdown hook → `ContextClosedEvent` →
       `SmartLifecycle` stop phases → connection draining (`server.shutdown=graceful`,
       `spring.lifecycle.timeout-per-shutdown-phase`) → pool close → JVM exit. Where Kubernetes'
       `terminationGracePeriodSeconds` has to be larger. `[FLOW]` `[NUM]` `[X-REF 19]`
2.11.6 What never runs on `SIGKILL` / OOMKill, and the design consequence (idempotent restart).
       `[X-REF 06]`
2.11.7 Startup failure diagnosis: the `FailureAnalyzer` box, `ApplicationFailedEvent`,
       `--debug`, and the ten most common startup failures with their exact messages. `[DIAG]`
2.11.8 Container thread-safety: `DefaultSingletonBeanRegistry` uses a `ConcurrentHashMap` for
       `singletonObjects` (initial capacity **256**) and per-bean creation guarding; two threads
       calling `getBean` on an uncreated prototype-scoped or lazily-created singleton concurrently.
       `[NUM]` `[SOURCE]` `[X-REF 05]`
2.11.9 The historical global singleton-creation lock and the 6.2 **lenient creation** rework
       (`lenientCreationLock`, `singletonsInLenientCreation`, `currentCreationThreads`) that
       removed a class of startup deadlocks with background/lazy initialisation. `[RESEARCH]`
       `[SOURCE]` `[VERSION-TRAP]`
2.11.10 Deadlock at startup: two threads lazily creating beans that depend on each other, or a
        `@PostConstruct` that blocks on an executor whose threads also create beans. How to read it
        in a thread dump. `[DIAG]` `[X-REF 06]`
2.11.11 Are beans thread-safe? Only if you wrote them that way. The container guarantees safe
        *publication* of fully initialised singletons; it guarantees nothing about your mutable
        fields. `[PROVE]` `[X-REF 05]`

*(11 leaves)*

## §2.12 Testing the container

2.12.1 The three levels: plain JUnit with `new` (no Spring at all — the reward for constructor
       injection), a sliced context, a full `@SpringBootTest`. `[X-REF 16]`
2.12.2 `@SpringBootTest` `webEnvironment` values: `MOCK`, `RANDOM_PORT`, `DEFINED_PORT`, `NONE`.
       `[API]`
2.12.3 The slice annotations by name: `@WebMvcTest`, `@WebFluxTest`, `@DataJpaTest`,
       `@DataJdbcTest`, `@JdbcTest`, `@DataRedisTest`, `@JsonTest`, `@RestClientTest`,
       `@DataMongoTest`, `@GraphQlTest`. Each loads a *filtered* set of auto-configurations.
       `[API]` `[X-REF 16]`
2.12.4 Bean overriding in tests: `@MockitoBean` / `@MockitoSpyBean` (Framework 6.2, replacing
       Boot's `@MockBean`/`@SpyBean` which are deprecated), `@TestBean`, `@TestConfiguration`,
       `@Primary` test beans. `[VERSION-TRAP]` `[RESEARCH]` `[X-REF 16]`
2.12.5 **Every bean override changes the context cache key**, so a `@MockitoBean` in one test class
       forks a whole new context. This is the #1 cause of slow Spring test suites. `[TRAP]`
       `[PROVE]`
2.12.6 `@DirtiesContext` and its modes (`BEFORE_CLASS`, `AFTER_CLASS`, `BEFORE_EACH_TEST_METHOD`,
       `AFTER_EACH_TEST_METHOD`, `AFTER_METHOD`), and why it should be a last resort.
2.12.7 `@DynamicPropertySource` for Testcontainers wiring, and the fact that it too is part of the
       cache key. `[X-REF 16]`
2.12.8 `@Transactional` on a test rolls back after each method; `@Commit`/`@Rollback(false)`;
       `TestTransaction` for manual control; why this hides `AFTER_COMMIT` listeners entirely.
       `[TRAP]`
2.12.9 `ApplicationContextRunner` for testing configuration classes without a real context —
       the fastest container test there is. `[X-REF §1.21.18]`
2.12.10 Asserting on the context: `assertThat(context).hasSingleBean(X.class)`,
        `.doesNotHaveBean(...)`, `.getFailure()`, `.hasBean("name")`. `[API]`

*(10 leaves)*

## §2.13 Observing the container at runtime

2.13.1 `/actuator/beans` — the full definition dump with scope, type, dependencies, and resource.
       How to answer "is my bean a proxy" from it. `[DIAG]`
2.13.2 `/actuator/conditions`, `/actuator/configprops`, `/actuator/env`, `/actuator/mappings`,
       `/actuator/startup`, `/actuator/metrics`. `[X-REF 20]`
2.13.3 `logging.level.org.springframework.beans.factory=DEBUG` /
       `org.springframework.transaction=TRACE` /
       `org.springframework.jdbc.datasource.DataSourceTransactionManager=DEBUG` — the three log
       categories that answer most "did it start a transaction" questions. `[PROP]` `[DIAG]`
2.13.4 Reading a transaction TRACE log: `Creating new transaction with name [...]`,
       `Participating in existing transaction`, `Suspending current transaction`,
       `Initiating transaction commit`, `Initiating transaction rollback`. `[DIAG]` `[SOURCE]`
2.13.5 Micrometer's container-adjacent metrics: `spring.data.repository.invocations`,
       `http.server.requests`, `hikaricp.connections.*`, `executor.*`,
       `spring.security.filterchains`. `[X-REF 20]`
2.13.6 `@Observed` and `ObservationRegistry` as Framework 6's replacement for `@Timed` on arbitrary
       beans — and yes, it is proxy-based. `[X-REF 20]` `[RESEARCH]`
2.13.7 Inspecting a live proxy in a debugger: `((Advised) bean).getAdvisors()`,
       `getTargetSource().getTarget()`, and the `CGLIB$CALLBACK_0` field. `[DIAG]`
2.13.8 Finding a bean's definition source when you do not know where it came from:
       `beanFactory.getBeanDefinition(name).getResourceDescription()`. `[API]` `[DIAG]`

*(8 leaves)*

## §2.14 Version delta — Spring 3 → 7, Boot 1 → 4

2.14.1 Spring 4.0: Java 8, generics-based injection, `@Conditional`, WebSocket.
2.14.2 Spring 4.2: `@EventListener`, `@TransactionalEventListener`, plain-object events.
2.14.3 Spring 4.3: implicit constructor injection for a single constructor, composed
       `@GetMapping`/`@PostMapping`. `[NUM]`
2.14.4 Spring 5.0: Java 8 baseline, WebFlux, functional bean registration, `@Nullable`, JUnit 5
       support.
2.14.5 Spring 5.2/5.3: `@Configuration(proxyBeanMethods)`, `RSocket`,
       `ApplicationStartup`, `JdbcTransactionManager`.
2.14.6 Spring 6.0: Java 17 baseline, `jakarta.*`, AOT + GraalVM native, `ProblemDetail`,
       HTTP interface clients, observability with Micrometer.
2.14.7 Spring 6.1: JdkClientHttpRequestFactory, `RestClient`, virtual-thread support,
       `@Scheduled(scheduler=...)`, built-in controller method validation, `Lifecycle` phase
       improvements. `[RESEARCH]`
2.14.8 Spring 6.2: `@Fallback`, `@Bean(bootstrap=BACKGROUND)`, lenient singleton locking,
       placeholder escaping, `@MockitoBean`/`@TestBean`, `TaskDecorator` for scheduled tasks,
       null-safety groundwork. `[RESEARCH]`
2.14.9 Spring 7.0 (Nov 2025): JSpecify null-safety across the portfolio, API versioning,
       `BeanRegistrar` programmatic registration, core resilience (`@Retryable`,
       `@ConcurrencyLimit`, `RetryTemplate`), `JmsClient`, `RestTestClient`, Jakarta EE 11.
       `[VERSION-TRAP]` `[RESEARCH]`
2.14.10 Boot 1.x → 2.0: CGLIB by default, `WebSecurityConfigurerAdapter`, Micrometer, reactive
        stack. `[VERSION-TRAP]`
2.14.11 Boot 2.1: bean-definition overriding disabled by default. `[NUM]` `[VERSION-TRAP]`
2.14.12 Boot 2.4: config-data processing rewritten; `spring.config.import`;
        `spring.config.activate.on-profile`; document ordering changed. `[VERSION-TRAP]`
2.14.13 Boot 2.6: circular references **disabled by default**;
        `spring.main.allow-circular-references`. `[NUM]` `[VERSION-TRAP]`
2.14.14 Boot 2.7: `@AutoConfiguration` and `AutoConfiguration.imports` introduced,
        `spring.factories` auto-config deprecated. `[VERSION-TRAP]`
2.14.15 Boot 3.0: Java 17, `jakarta.*`, `spring.factories` auto-config **removed**,
        `@ConstructorBinding` moved to the constructor, native images supported,
        `WebSecurityConfigurerAdapter` removed. `[VERSION-TRAP]`
2.14.16 Boot 3.1: `@ServiceConnection` and Testcontainers integration, Docker Compose support,
        `spring.docker.compose.*`. `[X-REF 16]` `[RESEARCH]`
2.14.17 Boot 3.2: virtual threads (`spring.threads.virtual.enabled`), `RestClient`, JVM checkpoint
        restore (CRaC). `[RESEARCH]` `[X-REF 06]`
2.14.18 Boot 3.4: `@ConditionalOnBooleanProperty`, structured logging, `RestTestClient` groundwork.
        `[RESEARCH]`
2.14.19 Boot 3.5: strict `.enabled` boolean parsing, profile-name validation,
        `taskExecutor` alias removed, `bootstrapExecutor` auto-configured, heapdump endpoint
        `access=NONE`, repeatable `@ConditionalOnProperty`, generic-aware
        `@ConditionalOnBean`. `[RESEARCH]` `[VERSION-TRAP]`
2.14.20 Boot 4.0 (Nov 2025): Spring Framework 7 baseline, Jackson 3, modularised autoconfigure
        jars, API versioning, null-safety. `[VERSION-TRAP]` `[RESEARCH]`
2.14.21 The "stale answer" list to sweep before an interview: `spring.factories`, JDK-proxy default,
        circular references allowed, `@ConstructorBinding` on the type, `javax.*`,
        `@MockBean`, `WebSecurityConfigurerAdapter`, `ListenableFuture`, `RestTemplate` as the
        recommended client. `[TRAP]` `[VERSION-TRAP]`

*(21 leaves)*

## §2.15 When not to use Spring, and the anti-pattern catalogue

2.15.1 When a plain `main` + manual wiring is better: a CLI, a lambda with a 50 ms cold-start
       budget, a library. `[X-REF 18]`
2.15.2 Quarkus/Micronaut's build-time DI as the architectural contrast — the same annotations, no
       reflection, no runtime proxy generation. Say what Spring gains by paying at runtime.
       `[PROVE]`
2.15.3 The anti-pattern catalogue: field injection everywhere; `ApplicationContextAware` as a
       service locator; god `@Configuration`; `@Autowired` on a static field (silently does
       nothing); stateful singletons; `@Transactional` on the repository layer; `@Transactional`
       spanning an HTTP call; catching and swallowing inside a transaction; profiles holding
       secrets; `spring.main.allow-circular-references=true` as a fix; `@EnableWebMvc` in a Boot
       app; scanning `com` as a base package; one giant `application.yml` with every environment.
       `[TRAP]`
2.15.4 `@Autowired` on a `static` field — no error, permanently `null`. `[TRAP]`
2.15.5 The "Spring is magic" complaint answered mechanically: every behaviour in this guide is a
       named class you can breakpoint.

*(5 leaves)*

---

**PART 2 total: 9+10+8+10+8+13+8+8+8+9+11+10+8+21+5 = 146 leaves**

---

# PART 3 — UNDER THE HOOD

Every leaf in this part names a real class in `spring-beans`, `spring-context`, `spring-aop`,
`spring-tx` or `spring-boot`. The write pass reads the source, quotes short excerpts, and explains
them line by line. Target branch: `spring-framework` **6.2.x**, `spring-boot` **3.5.x**.

## §3.1 `AbstractApplicationContext.refresh()` — the twelve steps

3.1.1 The method is `synchronized` on `startupShutdownLock` (6.2 replaced the old
      `synchronized(startupShutdownMonitor)` block with a `ReentrantLock` plus a
      `startupShutdownThread` field). Quote the guard. `[SOURCE]` `[RESEARCH]`
3.1.2 Step 1 `prepareRefresh()`: records `startupDate`, clears `closed`, sets `active`, calls
      `initPropertySources()`, validates required properties
      (`getEnvironment().validateRequiredProperties()`), and initialises `earlyApplicationEvents`.
      `[SOURCE]`
3.1.3 Step 2 `obtainFreshBeanFactory()`: `refreshBeanFactory()` + `getBeanFactory()`. For
      `GenericApplicationContext` this just flips the `refreshed` flag; for
      `AbstractRefreshableApplicationContext` it destroys the old factory and reloads definitions.
      `[SOURCE]`
3.1.4 Step 3 `prepareBeanFactory(beanFactory)`: sets the bean classloader, the
      `StandardBeanExpressionResolver`, a `ResourceEditorRegistrar`, adds
      `ApplicationContextAwareProcessor`, marks six `*Aware` interfaces as
      `ignoreDependencyInterface`, registers the resolvable dependencies
      (`BeanFactory`, `ResourceLoader`, `ApplicationEventPublisher`, `ApplicationContext`), adds
      `ApplicationListenerDetector`, registers `LoadTimeWeaverAwareProcessor` if present, and
      registers the default `environment`, `systemProperties`, `systemEnvironment` and
      `applicationStartup` singletons. Explain every one of those. `[SOURCE]` `[FLOW]`
3.1.5 Why `ignoreDependencyInterface` exists: setters that the container fills via `Aware` must not
      also be autowire targets. `[PROVE]`
3.1.6 Step 4 `postProcessBeanFactory(beanFactory)`: the subclass hook — where the web contexts
      register `ServletContextAwareProcessor`, the `request`/`session` scopes, and the
      servlet-related resolvable dependencies. `[SOURCE]`
3.1.7 Step 5 `invokeBeanFactoryPostProcessors(beanFactory)` → `PostProcessorRegistrationDelegate`.
      The precise order: context-level `BeanDefinitionRegistryPostProcessor`s already added
      programmatically → bean-defined BDRPPs implementing `PriorityOrdered` → those implementing
      `Ordered` → the rest, **looped until no new ones appear** → then all
      `BeanFactoryPostProcessor`s in the same three-tier order. `[SOURCE]` `[FLOW]` `[PROVE]`
3.1.8 `ConfigurationClassPostProcessor` runs here as the first `PriorityOrdered` BDRPP — which is
      why every `@Bean` definition exists before any plain BFPP sees the factory. `[PROVE]`
3.1.9 Step 6 `registerBeanPostProcessors(beanFactory)`: same three-tier ordering, plus
      `MergedBeanDefinitionPostProcessor`s registered last, plus
      `ApplicationListenerDetector` re-registered at the very end so it is the outermost.
      Instantiating a BPP here is what makes its dependencies "not eligible for post-processing".
      `[SOURCE]` `[PROVE]` `[TRAP]`
3.1.10 Step 7 `initMessageSource()`: uses a `messageSource` bean if present, else a
       `DelegatingMessageSource` delegating to the parent. `[SOURCE]`
3.1.11 Step 8 `initApplicationEventMulticaster()`: uses an `applicationEventMulticaster` bean if
       present, else a new `SimpleApplicationEventMulticaster`. `[SOURCE]`
3.1.12 Step 9 `onRefresh()`: the subclass hook. In Boot's servlet context this is where
       `createWebServer()` runs — the embedded Tomcat is created **before** the remaining
       singletons are instantiated but **not started** until `finishRefresh`. `[SOURCE]`
       `[TRAP]`
3.1.13 Step 10 `registerListeners()`: statically registered listeners first, then listener **bean
       names** (registered by name so the beans are not created early), then the buffered
       `earlyApplicationEvents` are published. `[SOURCE]` `[PROVE]`
3.1.14 Step 11 `finishBeanFactoryInitialization(beanFactory)`: registers the `conversionService`
       bean if one exists under that exact name, adds a default embedded-value resolver if no
       `PropertySourcesPlaceholderConfigurer` was registered, instantiates
       `LoadTimeWeaverAware` beans eagerly, freezes the configuration
       (`beanFactory.freezeConfiguration()`), then `preInstantiateSingletons()`. `[SOURCE]`
3.1.15 `preInstantiateSingletons()`: iterates `beanDefinitionNames` in **registration order**,
       skips abstract/lazy/non-singleton, calls `getBean` (dereferencing `FactoryBean`s only when
       `SmartFactoryBean.isEagerInit()`), then makes a second pass calling
       `SmartInitializingSingleton.afterSingletonsInstantiated()`. In 6.2 it also handles
       background-bootstrap beans and awaits them. `[SOURCE]` `[FLOW]` `[RESEARCH]`
3.1.16 Step 12 `finishRefresh()`: `clearResourceCaches()`, `initLifecycleProcessor()`,
       `getLifecycleProcessor().onRefresh()` (starts `SmartLifecycle` beans by phase — this is
       where Tomcat actually accepts connections), `publishEvent(new ContextRefreshedEvent(this))`.
       `[SOURCE]`
3.1.17 The `catch (BeansException ex)` block: `destroyBeans()`, `cancelRefresh(ex)`,
       `resetCommonCaches()`, rethrow. Why a failed startup still runs `@PreDestroy` on the beans
       that were created. `[SOURCE]` `[PROVE]`
3.1.18 The `finally` block: `contextRefresh.end()` and clearing `startupShutdownThread`.
3.1.19 `close()` / `doClose()` in the same detail: publish `ContextClosedEvent` →
       `lifecycleProcessor.onClose()` → `destroyBeans()` → `closeBeanFactory()` →
       `onClose()` → deregister the shutdown hook → set `active = false`. `[SOURCE]`
3.1.20 `destroySingletons()` destroys in **reverse registration order** and follows
       `dependentBeanMap` so a bean's dependents die before it does. `[SOURCE]` `[PROVE]`

*(20 leaves)*

## §3.2 `DefaultListableBeanFactory` internals

3.2.1 The class hierarchy walked bottom-up: `SimpleAliasRegistry` →
      `DefaultSingletonBeanRegistry` → `FactoryBeanRegistrySupport` → `AbstractBeanFactory` →
      `AbstractAutowireCapableBeanFactory` → `DefaultListableBeanFactory`. Each layer adds exactly
      one responsibility. `[SOURCE]`
3.2.2 The core maps: `beanDefinitionMap` (`ConcurrentHashMap`, capacity **256**),
      `beanDefinitionNames` (`ArrayList`, capacity **256** — the iteration order that decides
      instantiation order), `mergedBeanDefinitions`, `allBeanNamesByType`,
      `singletonBeanNamesByType`, `manualSingletonNames`, `resolvableDependencies`. `[NUM]`
      `[SOURCE]`
3.2.3 `frozenBeanDefinitionNames` and `configurationFrozen` — the snapshot taken by
      `freezeConfiguration()` that makes post-refresh type lookups allocation-free. `[SOURCE]`
3.2.4 `getBean` → `doGetBean(name, requiredType, args, typeCheckOnly)` walked line by line:
      `transformedBeanName` (strip `&`, resolve alias) → `getSingleton(beanName)` →
      if found, `getObjectForBeanInstance` (unwrap `FactoryBean`) → else check the parent factory →
      `markBeanAsCreated` → `getMergedLocalBeanDefinition` → `checkMergedBeanDefinition` →
      resolve `dependsOn` → dispatch on scope (singleton / prototype / other). `[SOURCE]`
      `[FLOW]`
3.2.5 `getObjectForBeanInstance` and `FactoryBeanRegistrySupport.factoryBeanObjectCache` — why a
      singleton `FactoryBean`'s product is cached and a prototype one's is not. `[SOURCE]`
3.2.6 `prototypesCurrentlyInCreation` (a `NamedThreadLocal`) and the prototype circular-dependency
      failure that cannot be resolved. `[SOURCE]` `[PROVE]`
3.2.7 Scope dispatch: `scopes.get(scopeName).get(beanName, objectFactory)` and the
      `IllegalStateException: No Scope registered for scope name 'request'` when the scope is
      missing. `[DIAG]` `[TRAP]`
3.2.8 `resolveDependency(DependencyDescriptor, ...)` and
      `doResolveDependency`: shortcut resolution, `@Value` handling via the embedded value
      resolver, multi-element resolution (`resolveMultipleBeans`), `findAutowireCandidates`,
      `determineAutowireCandidate`. `[SOURCE]` `[FLOW]`
3.2.9 `determineAutowireCandidate`: `determinePrimaryCandidate` → `determineHighestPriorityCandidate`
      → fallback to name match. Where `@Fallback` is filtered out. `[SOURCE]`
3.2.10 `QualifierAnnotationAutowireCandidateResolver` — how `@Qualifier` and custom qualifier
       annotations are actually matched, including matching against the bean *name* as a fallback.
       `[SOURCE]`
3.2.11 `ContextAnnotationAutowireCandidateResolver` and `getLazyResolutionProxyIfNecessary` — the
       class that turns `@Lazy` at an injection point into a `TargetSource`-backed proxy.
       `[SOURCE]` `[PROVE]`
3.2.12 `ResolvableType` and `GenericTypeResolver` — how `List<Order>` versus `List<User>` is
       distinguished despite erasure, reading the `Signature` attribute. `[X-REF 06]` `[SOURCE]`
3.2.13 `getBeanNamesForType` and the `allBeanNamesByType` cache: the first call is O(definitions)
       and every later call is O(1) — the reason freezing matters. `[PROVE]`
3.2.14 `registerResolvableDependency` and why `ApplicationContext` is injectable without a
       definition. `[SOURCE]`
3.2.15 `BeanFactory.FACTORY_BEAN_PREFIX = "&"` and `getBean("&myFactory")`. `[NUM]` `[SOURCE]`
3.2.16 Serialization support: `SerializedBeanFactoryReference` and the `serializationId` — a corner
       you will never use but which explains a field you will see.

*(16 leaves)*

## §3.3 Bean creation — `createBean` → `doCreateBean` → `initializeBean`

3.3.1 `createBean`: `resolveBeanClass` → `prepareMethodOverrides` (this is where `@Lookup` and
      `replaced-method` are set up) → `resolveBeforeInstantiation` → `doCreateBean`. `[SOURCE]`
3.3.2 `resolveBeforeInstantiation` → `applyBeanPostProcessorsBeforeInstantiation`: if any
      `InstantiationAwareBeanPostProcessor` returns non-null, the entire creation path is
      **short-circuited** and only `postProcessAfterInitialization` runs. This is the hook AOP
      frameworks and mocking libraries use to substitute an object wholesale. `[SOURCE]`
      `[PROVE]`
3.3.3 `doCreateBean` step 1 — `createBeanInstance`: `obtainFromSupplier` (the
      `registerBean(Class, Supplier)` path) → `instantiateUsingFactoryMethod` (the `@Bean` path) →
      `determineConstructorsFromBeanPostProcessors`
      (`SmartInstantiationAwareBeanPostProcessor.determineCandidateConstructors`, implemented by
      `AutowiredAnnotationBeanPostProcessor`) → `autowireConstructor` or
      `instantiateBean` (no-arg). `[SOURCE]` `[FLOW]`
3.3.4 `ConstructorResolver.autowireConstructor`: candidate sorting (public first, then descending
      parameter count), `resolveConstructorArguments`, ambiguity detection, and the
      `factoryBeanInstanceCache`. `[SOURCE]`
3.3.5 `SimpleInstantiationStrategy` versus `CglibSubclassingInstantiationStrategy` — the latter is
      used only when method overrides (`@Lookup`) exist. `[SOURCE]`
3.3.6 `doCreateBean` step 2 — `applyMergedBeanDefinitionPostProcessors`: this is where
      `AutowiredAnnotationBeanPostProcessor.postProcessMergedBeanDefinition` builds the
      `InjectionMetadata` (the cached list of annotated fields and methods) and where
      `CommonAnnotationBeanPostProcessor` finds `@PostConstruct`/`@PreDestroy`/`@Resource`.
      `[SOURCE]`
3.3.7 `InjectionMetadata` / `InjectedElement` / `AutowiredFieldElement` / `AutowiredMethodElement`,
      including the per-element `cached` + `cachedFieldValue` shortcut that makes repeated
      prototype creation cheap. `[SOURCE]` `[PROVE]`
3.3.8 `doCreateBean` step 3 — early singleton exposure:
      `earlySingletonExposure = (mbd.isSingleton() && this.allowCircularReferences &&
      isSingletonCurrentlyInCreation(beanName))`, then
      `addSingletonFactory(beanName, () -> getEarlyBeanReference(beanName, mbd, bean))`. Quote it.
      `[SOURCE]` `[NUM]`
3.3.9 `doCreateBean` step 4 — `populateBean`: `postProcessAfterInstantiation` (returning `false`
      skips property population entirely), `autowireByName`/`autowireByType` for the XML modes,
      then `postProcessProperties` (where `AutowiredAnnotationBeanPostProcessor` injects), then
      `applyPropertyValues` via `BeanWrapperImpl`. `[SOURCE]` `[FLOW]`
3.3.10 `BeanWrapperImpl`, `PropertyAccessor`, `TypeConverterDelegate` — the property-setting and
       conversion machinery, including nested property paths (`a.b[0].c`). `[SOURCE]`
3.3.11 `doCreateBean` step 5 — `initializeBean`: `invokeAwareMethods` (`BeanNameAware`,
       `BeanClassLoaderAware`, `BeanFactoryAware` only) →
       `applyBeanPostProcessorsBeforeInitialization` → `invokeInitMethods` →
       `applyBeanPostProcessorsAfterInitialization`. Quote the method. `[SOURCE]`
3.3.12 `invokeInitMethods`: `InitializingBean.afterPropertiesSet()` then the custom
       `initMethodName` (reflectively, honouring `enforceInitMethod`). `@PostConstruct` is **not**
       here — it ran as a `BeanPostProcessor` before initialization. `[SOURCE]` `[PROVE]`
3.3.13 `doCreateBean` step 6 — the circular-reference consistency check: if the bean was exposed
       early and then *wrapped* by AOP, and `allowRawInjectionDespiteWrapping` is false, Spring
       throws `BeanCurrentlyInCreationException` with the message
       `"...has been injected into other beans [...] in its raw version as part of a circular
       reference, but has eventually been wrapped. This means that said other beans do not use the
       final version of the bean."` Quote and explain it — this is the error people cannot decode.
       `[SOURCE]` `[DIAG]` `[TRAP]`
3.3.14 `doCreateBean` step 7 — `registerDisposableBeanIfNecessary` and `DisposableBeanAdapter`:
       which of `@PreDestroy`, `DisposableBean`, `destroyMethodName` and the **inferred**
       `close`/`shutdown` apply, and the `AutoCloseable` inference rule. `[SOURCE]`
3.3.15 `requiresDestruction` and why prototypes are excluded — the definitive source-level answer
       to "why isn't `@PreDestroy` called on my prototype". `[SOURCE]` `[PROVE]`
3.3.16 `BeanCreationException` wrapping: how the real cause ends up three `Caused by` levels down,
       and how to read the chain `UnsatisfiedDependencyException` → `BeanCreationException` →
       your `NullPointerException`. `[DIAG]`

*(16 leaves)*

## §3.4 The three-level cache and circular-dependency resolution

3.4.1 The three maps with their exact declarations and capacities:
      `singletonObjects` (`ConcurrentHashMap<String,Object>`, **256**),
      `earlySingletonObjects` (`ConcurrentHashMap<String,Object>`, **16**),
      `singletonFactories` (`ConcurrentHashMap<String,ObjectFactory<?>>`, **16**). `[NUM]`
      `[SOURCE]`
3.4.2 The supporting state: `registeredSingletons`
      (`Collections.synchronizedSet(new LinkedHashSet<>(256))` — the destruction order),
      `singletonsCurrentlyInCreation` (`ConcurrentHashMap.newKeySet(16)`),
      `inCreationCheckExclusions`, `disposableBeans` (`LinkedHashMap`),
      `dependentBeanMap` (**64**), `dependenciesForBeanMap` (**64**), `suppressedExceptions`.
      `[NUM]` `[SOURCE]`
3.4.3 `getSingleton(String beanName, boolean allowEarlyReference)` quoted verbatim and read line by
      line: L1 hit → return; else if currently in creation → L2 hit → return; else if
      `allowEarlyReference` → L3 factory → `getObject()` → promote to L2, remove from L3.
      `[SOURCE]` `[FLOW]`
3.4.4 `getSingleton(String, ObjectFactory<?>)` — the creation path:
      `beforeSingletonCreation` (adds to `singletonsCurrentlyInCreation`, throws
      `BeanCurrentlyInCreationException` if already present) → `singletonFactory.getObject()` →
      `afterSingletonCreation` → `addSingleton` (L1 put, L2/L3 remove, `registeredSingletons` add).
      `[SOURCE]` `[FLOW]`
3.4.5 **The proof that field/setter cycles resolve and constructor cycles do not.** Walk A→B→A
      step by step for both, showing exactly where the L3 factory is registered relative to where
      the dependency is needed. This is the single most-asked internals question in Spring
      interviews. `[PROVE]` `[FLOW]`
3.4.6 **Why three levels and not two.** The naive answer "two would do" fails when the bean must be
      AOP-proxied: L3 holds a *factory* so `getEarlyBeanReference` runs at most once and lazily,
      producing the proxy only if someone actually needs the early reference. With only L2 you
      would have to create the proxy eagerly for every bean. `[PROVE]` `[SOURCE]`
3.4.7 `getEarlyBeanReference` on `SmartInstantiationAwareBeanPostProcessor`, implemented by
      `AbstractAutoProxyCreator` with its `earlyProxyReferences` map — and the fact that
      `postProcessAfterInitialization` then *skips* proxy creation for anything already in that
      map. `[SOURCE]` `[PROVE]`
3.4.8 The case the three-level cache cannot save: `@Async` on a bean in a cycle. The async proxy is
      created by `AsyncAnnotationBeanPostProcessor` at `postProcessAfterInitialization`, not via
      `getEarlyBeanReference`, so the early reference is the raw object and the wrapping check
      (§3.3.13) fires. `[TRAP]` `[PROVE]` `[RESEARCH]`
3.4.9 `allowCircularReferences` field default is `true` in `AbstractAutowireCapableBeanFactory`;
      Spring Boot sets it to **false** since 2.6 via
      `spring.main.allow-circular-references`. Both statements are true and people conflate them.
      `[NUM]` `[VERSION-TRAP]` `[SOURCE]`
3.4.10 `allowRawInjectionDespiteWrapping` (default `false`) and what setting it true actually
       permits. `[NUM]`
3.4.11 Reading the Boot circular-reference failure report: the
       `┌─────┐ | a defined in file [...] ↑ ↓ | b defined in file [...] └─────┘` diagram, and the
       three actions Boot suggests. `[DIAG]`
3.4.12 The real fixes ranked: extract the shared logic into a third bean; invert one direction with
       an event; use `ObjectProvider` for the lazier side; `@Lazy` on one injection point as the
       last resort. `spring.main.allow-circular-references=true` is a "we know it is broken"
       marker, not a fix. `[TRAP]`
3.4.13 `dependentBeanMap` / `dependenciesForBeanMap` and `isDependent` — the graph used both for
       `@DependsOn` cycle detection and for reverse-order destruction. `[SOURCE]`
3.4.14 The 6.2 lenient-creation machinery (`lenientCreationLock`, `lenientCreationFinished`,
       `singletonsInLenientCreation`, `lenientWaitingThreads`, `currentCreationThreads`) — what
       deadlock it removes when two threads create interdependent singletons concurrently.
       `[SOURCE]` `[RESEARCH]` `[VERSION-TRAP]`

*(14 leaves)*

## §3.5 `ConfigurationClassPostProcessor` and configuration parsing

3.5.1 It is a `BeanDefinitionRegistryPostProcessor` **and** `PriorityOrdered` with order
      `Ordered.LOWEST_PRECEDENCE - 1`, registered by `AnnotationConfigUtils.registerAnnotationConfigProcessors`
      under the name
      `org.springframework.context.annotation.internalConfigurationAnnotationProcessor`. `[NUM]`
      `[SOURCE]`
3.5.2 The other internal processor bean names registered at the same time:
      `internalAutowiredAnnotationProcessor`, `internalCommonAnnotationProcessor`,
      `internalEventListenerProcessor`, `internalEventListenerFactory`,
      `internalPersistenceAnnotationProcessor`. `[NUM]` `[SOURCE]`
3.5.3 `checkConfigurationClassCandidate`: full mode (`@Configuration` with
      `proxyBeanMethods=true`) sets the attribute `CONFIGURATION_CLASS_ATTRIBUTE` to `"full"`;
      lite mode (`@Component`, `@ComponentScan`, `@Import`, `@ImportResource`, or any `@Bean`
      method) sets it to `"lite"`. Quote the method. `[SOURCE]` `[NUM]`
3.5.4 `ConfigurationClassParser.parse` and the recursive `doProcessConfigurationClass`, in its
      documented order: member (nested) classes → `@PropertySource` → `@ComponentScan` (recursing
      into each newly found configuration class) → `@Import` → `@ImportResource` → `@Bean` methods
      → interface default `@Bean` methods → superclass. `[SOURCE]` `[FLOW]`
3.5.5 `ConditionEvaluator.shouldSkip` and the two `ConfigurationPhase`s
      (`PARSE_CONFIGURATION` vs `REGISTER_BEAN`) — the reason a condition can be evaluated twice
      with different answers. `[SOURCE]` `[PROVE]`
3.5.6 `DeferredImportSelectorHandler` / `DeferredImportSelectorGroupingHandler`: deferred selectors
      are collected during parsing and processed **after** all regular configuration, grouped by
      `Group`. `AutoConfigurationImportSelector.AutoConfigurationGroup` is that group. `[SOURCE]`
      `[PROVE]`
3.5.7 `ConfigurationClassBeanDefinitionReader.loadBeanDefinitions` → `loadBeanDefinitionsForBeanMethod`,
      producing a `ConfigurationClassBeanDefinition` with `factoryBeanName` = the configuration
      class and `factoryMethodName` = the `@Bean` method. The "overriding" rule between a scanned
      bean and a `@Bean` of the same name lives here. `[SOURCE]`
3.5.8 `enhanceConfigurationClasses` runs in `postProcessBeanFactory` (the second callback), finds
      every definition with the `"full"` attribute, and replaces its bean class with the
      CGLIB-enhanced subclass. `[SOURCE]`
3.5.9 `ConfigurationClassEnhancer`: two callbacks, `BeanMethodInterceptor` and
      `BeanFactoryAwareMethodInterceptor`, plus a `CALLBACK_FILTER`, plus the injected
      `$$beanFactory` field and the `EnhancedConfiguration` marker interface. `[SOURCE]`
3.5.10 `BeanMethodInterceptor.intercept` walked through: if the currently-invoked factory method
       *is* this method (i.e. the container itself is calling it), invoke the super method;
       otherwise `resolveBeanReference` — look the bean up from the factory and return the
       singleton. Quote `isCurrentlyInvokedFactoryMethod`. `[SOURCE]` `[PROVE]`
3.5.11 The `FactoryBean` special case in `resolveBeanReference`: when a `@Bean` method returns a
       `FactoryBean`, the interceptor returns a **proxy of the FactoryBean** whose `getObject()`
       delegates to the container. Explain why. `[SOURCE]` `[PROVE]`
3.5.12 What lite mode gives up, precisely, and why Boot's auto-configurations accept the trade:
       one fewer CGLIB class per configuration, no `$$beanFactory` field, faster startup, and no
       inter-method singleton guarantee. `[NUM]` `[PROVE]`
3.5.13 `ConfigurationClassPostProcessor` and AOT: `ConfigurationClassPostProcessor` contributes
       `BeanFactoryInitializationAotContribution`s so the parsing work happens at build time.
       `[X-REF §3.21]`
3.5.14 `ComponentScanAnnotationParser` → `ClassPathBeanDefinitionScanner.doScan` →
       `findCandidateComponents` → `isCandidateComponent` (independent, concrete, or an abstract
       class with `@Lookup`) → `AnnotationScopeMetadataResolver` →
       `AnnotationConfigUtils.processCommonDefinitionAnnotations` (`@Lazy`, `@Primary`,
       `@Fallback`, `@DependsOn`, `@Role`, `@Description`). `[SOURCE]` `[FLOW]`
3.5.15 `SimpleMetadataReaderFactory` / `CachingMetadataReaderFactory` and ASM-based
       `AnnotationMetadata` — scanning never loads a class. `[SOURCE]` `[X-REF 06]`

*(15 leaves)*

## §3.6 Annotation-driven injection internals

3.6.1 `AutowiredAnnotationBeanPostProcessor`: the `autowiredAnnotationTypes` set
      (`@Autowired`, `@Value`, and `jakarta.inject.Inject` when present), the
      `requiredParameterName`/`requiredParameterValue` fields, and the
      `injectionMetadataCache`. `[SOURCE]`
3.6.2 `determineCandidateConstructors` in full — the source of the §1.6.3 algorithm, including the
      `candidateConstructorsCache` and the primary-constructor lookup for Kotlin/records.
      `[SOURCE]`
3.6.3 `AutowiredFieldElement.inject`: `field.setAccessible(true)`, `resolveDependency`, and the
      `cachedFieldValue` shortcut (`ShortcutDependencyDescriptor`). `[SOURCE]`
3.6.4 `AutowiredMethodElement.inject` and the "skip the call entirely if not required and
      unresolved" branch. `[SOURCE]`
3.6.5 `CommonAnnotationBeanPostProcessor`: `@PostConstruct`/`@PreDestroy` discovery via
      `LifecycleMetadata`, and `@Resource` resolution (`ResourceElement`,
      `autowireResource`, `fallbackToDefaultTypeMatch`). `[SOURCE]`
3.6.6 `InitDestroyAnnotationBeanPostProcessor` as the superclass that actually invokes
      `@PostConstruct`/`@PreDestroy`, and the `lifecycleMetadataCache`. `[SOURCE]`
3.6.7 Why `@PostConstruct` is a `BeanPostProcessor` and not part of `invokeInitMethods` — and the
      ordering consequence (`@PostConstruct` before `afterPropertiesSet`). `[PROVE]`
3.6.8 `@Lookup` handling: `LookupOverride`, `MethodOverrides`, and
      `CglibSubclassingInstantiationStrategy.LookupOverrideMethodInterceptor`. `[SOURCE]`
3.6.9 `EventListenerMethodProcessor` implements `SmartInitializingSingleton` — which is why
      `@EventListener` methods are discovered after all singletons exist, and why a lazy bean's
      listeners are never registered. `[SOURCE]` `[PROVE]`
3.6.10 `ApplicationListenerDetector` — the `MergedBeanDefinitionPostProcessor` that registers
       `ApplicationListener` **beans** (as opposed to `@EventListener` methods) and de-registers
       them on destruction. `[SOURCE]`

*(10 leaves)*

## §3.7 AOP proxy creation internals

3.7.1 `AbstractAutoProxyCreator` is a `SmartInstantiationAwareBeanPostProcessor`; the entry points
      are `postProcessBeforeInstantiation`, `getEarlyBeanReference`, and
      `postProcessAfterInitialization` → `wrapIfNecessary`. `[SOURCE]`
3.7.2 `wrapIfNecessary`: skip if in `targetSourcedBeans`, skip if `advisedBeans` says no, skip
      infrastructure classes (`isInfrastructureClass`: `Advice`, `Pointcut`, `Advisor`,
      `AopInfrastructureBean`) and `shouldSkip`, then
      `getAdvicesAndAdvisorsForBean` → `createProxy`. `[SOURCE]` `[FLOW]`
3.7.3 `AbstractAdvisorAutoProxyCreator.findEligibleAdvisors`: `findCandidateAdvisors` →
      `findAdvisorsThatCanApply` (`AopUtils.canApply` → `ClassFilter.matches` then
      `MethodMatcher.matches` over every method) → `extendAdvisors` (adds
      `ExposeInvocationInterceptor.ADVISOR` at position 0) → `sortAdvisors`. `[SOURCE]`
      `[FLOW]`
3.7.4 `ExposeInvocationInterceptor` and why it must be first — it binds the current
      `MethodInvocation` to a `ThreadLocal` so `@AfterReturning(returning=)` style binding and
      AspectJ pointcut runtime tests can work. `[SOURCE]` `[PROVE]`
3.7.5 `AnnotationAwareAspectJAutoProxyCreator` → `BeanFactoryAspectJAdvisorsBuilder.buildAspectJAdvisors`:
      scans all bean names for `@Aspect`, builds `InstantiationModelAwarePointcutAdvisorImpl` per
      advice method, caches by aspect bean name. `[SOURCE]`
3.7.6 `ReflectiveAspectJAdvisorFactory.METHOD_COMPARATOR` — the source of the intra-aspect advice
      precedence in §1.13.4. Quote it. `[SOURCE]` `[PROVE]` `[RESEARCH]`
3.7.7 `createProxy` → `ProxyFactory` populated with `copyFrom(this)`, `proxyTargetClass`,
      the advisors, the `TargetSource`, `frozen`, then `getProxy(classLoader)`. `[SOURCE]`
3.7.8 `DefaultAopProxyFactory.createAopProxy` quoted in full: the `NativeDetector.inNativeImage()`
      branch, `optimize || proxyTargetClass || hasNoUserSuppliedProxyInterfaces` → `ObjenesisCglibAopProxy`,
      else `JdkDynamicAopProxy`; plus the `IllegalArgumentException` for interfaces and lambdas.
      `[SOURCE]` `[NUM]`
3.7.9 `JdkDynamicAopProxy.invoke` line by line: `equals`/`hashCode` special-casing, `DecoratingProxy`,
      `Advised` method routing, `exposeProxy` handling, `getInterceptorsAndDynamicInterceptionAdvice`,
      then either direct reflective invocation (empty chain) or
      `new ReflectiveMethodInvocation(...).proceed()`. `[SOURCE]`
3.7.10 `ReflectiveMethodInvocation.proceed()` quoted: the `currentInterceptorIndex` counter, the
       `InterceptorAndDynamicMethodMatcher` runtime-match branch, and
       `invokeJoinpoint()` at the end of the chain. This tiny method **is** the interceptor chain.
       `[SOURCE]` `[PROVE]`
3.7.11 `CglibAopProxy.getProxy`: `Enhancer` setup, `setSuperclass`, `setInterfaces`,
       `setNamingPolicy` (`SpringNamingPolicy` — the `$$SpringCGLIB$$` suffix in 6.0+),
       `setStrategy`, `getCallbacks()`, `setCallbackFilter(ProxyCallbackFilter)`. `[SOURCE]`
       `[VERSION-TRAP]`
3.7.12 The seven CGLIB callbacks by index: `AOP_PROXY` (`DynamicAdvisedInterceptor`),
       `INVOKE_TARGET` (`StaticUnadvisedInterceptor`), `NO_OVERRIDE` (`SerializableNoOp`),
       `DISPATCH_TARGET` (`StaticDispatcher`), `DISPATCH_ADVISED` (`AdvisedDispatcher`),
       `INVOKE_EQUALS` (`EqualsInterceptor`), `INVOKE_HASHCODE` (`HashCodeInterceptor`).
       `[SOURCE]` `[NUM]` `[RESEARCH]`
3.7.13 `DynamicAdvisedInterceptor.intercept` and `CglibMethodInvocation` — the CGLIB twin of
       §3.7.10, using `MethodProxy.invoke` instead of reflection. `[SOURCE]`
3.7.14 `ObjenesisCglibAopProxy.createProxyClassAndInstance` — instantiating the subclass **without**
       calling any constructor, and the fallback to a real constructor call when Objenesis fails.
       This is the source-level answer to "does the constructor run twice". `[SOURCE]` `[PROVE]`
       `[TRAP]`
3.7.15 `AdvisedSupport.getInterceptorsAndDynamicInterceptionAdvice` and the
       `AdvisorChainFactory` **method cache** (`methodCache`) — the chain is computed once per
       method, not per call. `[SOURCE]` `[PROVE]`
3.7.16 The advice adapters: `MethodBeforeAdviceAdapter`, `AfterReturningAdviceAdapter`,
       `ThrowsAdviceAdapter`, `DefaultAdvisorAdapterRegistry` — how non-`MethodInterceptor` advice
       becomes an interceptor. `[SOURCE]`
3.7.17 `AspectJExpressionPointcut` and the fact that it delegates to the real AspectJ
       `PointcutParser` with a restricted set of supported primitives — which is why an
       unsupported designator throws `IllegalArgumentException` at startup. `[SOURCE]`
3.7.18 `AopProxyUtils.completeProxiedInterfaces` — the interfaces Spring silently adds:
       `SpringProxy`, `Advised` (unless `opaque`), `DecoratingProxy`. Their diagnostic value.
       `[SOURCE]`
3.7.19 Proxy class generation cost and the `Enhancer` cache; why thousands of proxied beans show up
       as metaspace and class-loading time. `[X-REF 06]` `[PROVE]`

*(19 leaves)*

## §3.8 `TransactionInterceptor` internals

3.8.1 `TransactionInterceptor implements MethodInterceptor`, delegating to
      `TransactionAspectSupport.invokeWithinTransaction`. `[SOURCE]`
3.8.2 `invokeWithinTransaction` walked through: `getTransactionAttributeSource()` →
      `getTransactionAttribute(method, targetClass)` → `determineTransactionManager` →
      `methodIdentification` → if the manager is a `CallbackPreferringPlatformTransactionManager`
      take the callback path, else `createTransactionIfNecessary` → `invocation.proceedWithInvocation()`
      in a try → `completeTransactionAfterThrowing` in the catch →
      `cleanupTransactionInfo` in the finally → `commitTransactionAfterReturning`. `[SOURCE]`
      `[FLOW]`
3.8.3 `AnnotationTransactionAttributeSource` + `SpringTransactionAnnotationParser`: the search
      order is **specific method → declaring class → interface method → interface class**, and the
      `AbstractFallbackTransactionAttributeSource.attributeCache` keyed by `MethodClassKey`.
      Quote the search order — it is the source-level answer to "does `@Transactional` on the
      interface work". `[SOURCE]` `[PROVE]` `[TRAP]`
3.8.4 `TransactionAttribute` / `RuleBasedTransactionAttribute` / `RollbackRuleAttribute` and
      `getDepth(Throwable)` — the "winning rule is the one with the shallowest inheritance
      distance" algorithm, with `NoRollbackRuleAttribute` as a subclass. `[SOURCE]` `[PROVE]`
3.8.5 `DefaultTransactionAttribute.rollbackOn(Throwable)`:
      `ex instanceof RuntimeException || ex instanceof Error`. Quote the one line that causes the
      most production bugs in this guide. `[SOURCE]` `[TRAP]`
3.8.6 `TransactionInfo` and the `transactionInfoHolder` `ThreadLocal` stack —
      `bindToThread`/`restoreThreadLocalStatus` is what makes nesting work. `[SOURCE]`
3.8.7 `AbstractPlatformTransactionManager.getTransaction`: `doGetTransaction` →
      `isExistingTransaction` → if existing, `handleExistingTransaction` (the propagation switch) →
      else the no-transaction propagation switch → `startTransaction` →
      `newTransactionStatus` → `doBegin` → `prepareSynchronization`. `[SOURCE]` `[FLOW]`
3.8.8 `handleExistingTransaction` per propagation: `NEVER` → throw; `NOT_SUPPORTED` → `suspend`;
      `REQUIRES_NEW` → `suspend` then `startTransaction`; `NESTED` → savepoint or nested begin;
      `SUPPORTS`/`REQUIRED`/`MANDATORY` → participate, with `validateExistingTransaction`
      optionally checking isolation and read-only mismatches. `[SOURCE]`
3.8.9 `validateExistingTransaction` and `setValidateExistingTransaction(true)` — the opt-in that
      turns a silently-ignored inner `isolation` attribute into a loud
      `IllegalTransactionStateException`. `[TRAP]` `[SOURCE]`
3.8.10 `suspend` / `resume` and `SuspendedResourcesHolder`: unbinding the resource,
       `TransactionSynchronizationManager.doSuspendSynchronization`, and restoring on completion.
       `[SOURCE]`
3.8.11 `DataSourceTransactionManager.doBegin`: `DataSourceUtils.getConnection` → `setAutoCommit(false)`
       → apply isolation and read-only via `DataSourceUtils.prepareConnectionForTransaction` →
       `TransactionSynchronizationManager.bindResource(dataSource, connectionHolder)`. `[SOURCE]`
3.8.12 `DataSourceUtils.getConnection` — the method every `JdbcTemplate` call goes through, and how
       it finds the thread-bound connection or takes a fresh one. This is the mechanism behind
       "the transaction is ambient". `[SOURCE]` `[PROVE]`
3.8.13 `processCommit`: `triggerBeforeCommit` → `triggerBeforeCompletion` → savepoint release or
       `doCommit` → `triggerAfterCommit` → `triggerAfterCompletion` → `cleanupAfterCompletion`.
       The `unexpectedRollback` check that throws `UnexpectedRollbackException` lives here.
       `[SOURCE]` `[FLOW]` `[PROVE]`
3.8.14 `processRollback` and `doSetRollbackOnly`; `globalRollbackOnParticipationFailure`
       (default `true`) — the flag that decides whether a participating failure poisons the outer
       transaction. Setting it false is the sanctioned escape hatch. `[NUM]` `[SOURCE]`
       `[TRAP]`
3.8.15 `TransactionSynchronizationManager`'s five `ThreadLocal`s: `resources`, `synchronizations`,
       `currentTransactionName`, `currentTransactionReadOnly`, `currentTransactionIsolationLevel`,
       `actualTransactionActive`. `[SOURCE]` `[NUM]` `[X-REF 05]`
3.8.16 `TransactionalApplicationListenerMethodAdapter` /
       `TransactionalApplicationListenerSynchronization` — how
       `@TransactionalEventListener` registers a `TransactionSynchronization` and fires in the
       right phase, and what `fallbackExecution=false` skips. `[SOURCE]` `[PROVE]`
3.8.17 `BeanFactoryTransactionAttributeSourceAdvisor` + `TransactionAttributeSourcePointcut` —
       the pointcut that decides which beans get the transaction proxy at all, registered by
       `ProxyTransactionManagementConfiguration`. `[SOURCE]`
3.8.18 `InfrastructureAdvisorAutoProxyCreator` and the `ROLE_INFRASTRUCTURE` filter — why
       `@EnableTransactionManagement` only considers infrastructure-role advisors. `[SOURCE]`
3.8.19 `TransactionAspectSupport.currentTransactionStatus()` and
       `currentTransactionInfo()` as the public escape hatches. `[API]`
3.8.20 The AspectJ mode implementation (`AnnotationTransactionAspect` in `spring-aspects`) and what
       it does differently — it advises the *execution* join point, so self-invocation works.
       `[PROVE]`

*(20 leaves)*

## §3.9 Scope, event and expression internals

3.9.1 `AbstractBeanFactory.scopes` map and `registerScope`; `ScopedProxyFactoryBean` +
      `SimpleBeanTargetSource` + `ScopedProxyUtils.createScopedProxy` (which renames the real
      definition to `scopedTarget.<name>`). Grep for `scopedTarget.` in `/actuator/beans`.
      `[SOURCE]` `[DIAG]`
3.9.2 `RequestScope` / `SessionScope` / `AbstractRequestAttributesScope` and
      `RequestAttributes.SCOPE_REQUEST = 0` / `SCOPE_SESSION = 1`. `[NUM]` `[SOURCE]`
3.9.3 `RequestContextHolder`'s two `ThreadLocal`s (`requestAttributesHolder` and
      `inheritableRequestAttributesHolder`) and `RequestContextFilter.setThreadContextInheritable`.
      `[SOURCE]` `[X-REF 05]`
3.9.4 `ServletRequestAttributes.requestDestructionCallbacks` and where the request-scope destruction
      callback is actually invoked (`requestCompleted()`). `[SOURCE]`
3.9.5 `SimpleThreadScope` source — a `NamedThreadLocal<Map<String,Object>>` whose
      `registerDestructionCallback` is a documented **no-op**. Quote the javadoc warning.
      `[SOURCE]` `[TRAP]`
3.9.6 `SimpleApplicationEventMulticaster.multicastEvent`: `resolveDefaultEventType` →
      `getApplicationListeners(event, type)` → for each, either `executor.execute` or
      `invokeListener` → `doInvokeListener` with `errorHandler` handling. `[SOURCE]`
3.9.7 `AbstractApplicationEventMulticaster.retrieverCache` keyed by `ListenerCacheKey(eventType,
      sourceType)` — listener resolution is cached, and `supportsEventType` uses `ResolvableType`.
      `[SOURCE]` `[PROVE]`
3.9.8 `ApplicationListenerMethodAdapter` — the object wrapping an `@EventListener` method,
      including `shouldHandle` (the SpEL `condition`), `resolveArguments`, and
      `handleResult` (publishing returned events). `[SOURCE]`
3.9.9 `PayloadApplicationEvent<T>` and `GenericApplicationListener` /
      `GenericApplicationListenerAdapter` — how a non-`ApplicationEvent` payload is type-matched.
      `[SOURCE]`
3.9.10 `SpelExpressionParser` → `Tokenizer` → `InternalSpelExpressionParser` → an AST of
       `SpelNodeImpl`s → `SpelExpression.getValue(ExpressionState)`. The compiled path:
       `SpelCompiler` generates a `CompiledExpression` subclass after
       `interpretedCount` exceeds a threshold in `MIXED` mode. `[SOURCE]` `[NUM]`
       `[RESEARCH]`
3.9.11 `StandardEvaluationContext`'s resolver chain: `PropertyAccessor`s (`ReflectivePropertyAccessor`
       with its `readerCache`), `BeanResolver` (`BeanFactoryResolver` — the `@bean` syntax),
       `TypeLocator`, `ConstructorResolver`, `MethodResolver`, `OperatorOverloader`,
       `TypeConverter`. `[SOURCE]`
3.9.12 `SimpleEvaluationContext.forReadOnlyDataBinding()` and the security argument restated at
       source level: no `TypeLocator`, no `ConstructorResolver`, no `BeanResolver`.
       `[SOURCE]` `[X-REF 13]`
3.9.13 `PropertyPlaceholderHelper.parseStringValue` — the recursive `${}` resolver, including
       `visitedPlaceholders` cycle detection (`IllegalArgumentException: Circular placeholder
       reference`) and the 6.2 escape character. `[SOURCE]` `[DIAG]` `[RESEARCH]`
3.9.14 `PropertySourcesPropertyResolver.getProperty` — iterate the sources in order, first
       non-null wins, then `convertValueIfNecessary` through the `ConversionService`. `[SOURCE]`
3.9.15 `GenericConversionService.converters` (a `Converters` object with a
       `ConvertiblePair`-keyed map plus a global set) and the `converterCache`; the
       `NO_OP_CONVERTER` and `NO_MATCH` sentinels. `[SOURCE]`

*(15 leaves)*

## §3.10 `SpringApplication.run()` internals

3.10.1 The constructor: `deduceMainApplicationClass()` (walks the stack for `main`),
       `deduceFromClasspath()` for `WebApplicationType`, then
       `getSpringFactoriesInstances` for `BootstrapRegistryInitializer`,
       `ApplicationContextInitializer` and `ApplicationListener` from
       `META-INF/spring.factories`. `[SOURCE]` `[FLOW]`
3.10.2 `run(String...)` step by step: create `DefaultBootstrapContext` → `getRunListeners` →
       `listeners.starting()` → `new DefaultApplicationArguments(args)` →
       `prepareEnvironment` → `configureIgnoreBeanInfo` → `printBanner` →
       `createApplicationContext` → `prepareContext` → `refreshContext` →
       `afterRefresh` → `listeners.started()` → `callRunners` → `listeners.ready()`.
       `[SOURCE]` `[FLOW]`
3.10.3 `prepareEnvironment`: `getOrCreateEnvironment` → `configureEnvironment`
       (`configurePropertySources` adds `defaultProperties`, `commandLineArgs`;
       `configureProfiles`) → `ConfigurationPropertySources.attach` →
       `listeners.environmentPrepared()` (**this is where `EnvironmentPostProcessor`s run**) →
       `bindToSpringApplication` → `convertEnvironment` if needed. `[SOURCE]`
3.10.4 `EnvironmentPostProcessorApplicationListener` and the `EnvironmentPostProcessor`
       implementations Boot ships: `ConfigDataEnvironmentPostProcessor`,
       `RandomValuePropertySourceEnvironmentPostProcessor`,
       `SpringApplicationJsonEnvironmentPostProcessor`,
       `SystemEnvironmentPropertySourceEnvironmentPostProcessor`,
       `CloudFoundryVcapEnvironmentPostProcessor`, `IntegrationPropertiesEnvironmentPostProcessor`,
       `DebugAgentEnvironmentPostProcessor`. `[SOURCE]` `[RESEARCH]`
3.10.5 `ConfigDataEnvironmentPostProcessor` → `ConfigDataEnvironment` →
       `ConfigDataLocationResolver` / `ConfigDataLoader` / `ConfigDataEnvironmentContributor`
       tree — the machinery behind `spring.config.import`, profile activation and multi-document
       ordering (Boot 2.4 rewrite). `[SOURCE]` `[RESEARCH]`
3.10.6 `ConfigurationPropertySources.attach` and the synthetic
       `configurationProperties` property source that makes relaxed binding work at all. `[SOURCE]`
       `[PROVE]`
3.10.7 `prepareContext`: `context.setEnvironment` → `postProcessApplicationContext`
       (registers the `beanNameGenerator`, `resourceLoader`, `conversionService`) →
       `applyInitializers` → `listeners.contextPrepared()` → register `springApplicationArguments`
       and `springBootBanner` singletons → set `allowBeanDefinitionOverriding` and
       `allowCircularReferences` → add `LazyInitializationBeanFactoryPostProcessor` if lazy →
       `load(context, sources)` → `listeners.contextLoaded()`. `[SOURCE]` `[FLOW]`
3.10.8 `refreshContext` → `refresh()` → §3.1, plus `shutdownHook.registerApplicationContext` when
       `registerShutdownHook` is true. `[SOURCE]`
3.10.9 `SpringApplicationShutdownHook` — one JVM hook for all contexts, with
       `SpringApplicationShutdownHandlers` for extra actions. `[SOURCE]`
3.10.10 `callRunners`: `ApplicationRunner` and `CommandLineRunner` beans merged and sorted with
        `AnnotationAwareOrderComparator`; an exception becomes an
        `IllegalStateException("Failed to execute ApplicationRunner")` and fails the app.
        `[SOURCE]` `[TRAP]`
3.10.11 `handleRunFailure` → `reportFailure` → `SpringBootExceptionReporter` →
        `FailureAnalyzers` → the boxed error report; then `listeners.failed()`,
        `context.close()`, and `ExitCodeGenerators`. `[SOURCE]` `[DIAG]`
3.10.12 `ServletWebServerApplicationContext.createWebServer` and
        `ServletWebServerFactory.getWebServer(ServletContextInitializer...)`; the
        `DispatcherServletRegistrationBean` and `ServletContextInitializerBeans`. `[SOURCE]`
3.10.13 The `WebServer` is created in `onRefresh` but **started** in `finishRefresh` via
        `WebServerStartStopLifecycle` — the reason a slow bean does not cause traffic to arrive
        early. `[SOURCE]` `[PROVE]`
3.10.14 `AutoConfigurationImportSelector` internals: `getAutoConfigurationEntry` →
        `getCandidateConfigurations` (`ImportCandidates.load`) → `removeDuplicates` →
        `getExclusions` → `checkExcludedClasses` → `getConfigurationClassFilter().filter(...)`
        (`OnClassCondition`, `OnBeanCondition`, `OnWebApplicationCondition` as
        `AutoConfigurationImportFilter`s using the metadata file) →
        `fireAutoConfigurationImportEvents`. `[SOURCE]` `[FLOW]`
3.10.15 `AutoConfigurationSorter`: sorts alphabetically, then by `@AutoConfigureOrder`, then
        topologically by `@AutoConfigureBefore`/`@AutoConfigureAfter`. Quote the three-stage sort —
        it explains why ordering is *stable* but not intuitive. `[SOURCE]` `[PROVE]`
3.10.16 `ConditionEvaluationReport` — how the report is accumulated
        (`recordConditionEvaluation`), stored as a bean named
        `autoConfigurationReport`, and printed by
        `ConditionEvaluationReportLoggingListener` on `ApplicationFailedEvent` or at DEBUG.
        `[SOURCE]` `[DIAG]`
3.10.17 `OnClassCondition`'s two-thread split for large candidate lists, and why condition
        evaluation is one of the measurable parts of startup. `[SOURCE]` `[RESEARCH]`
3.10.18 `SpringFactoriesLoader` — `META-INF/spring.factories` is **still** used for everything
        except auto-configuration (listeners, initializers, `EnvironmentPostProcessor`s,
        `FailureAnalyzer`s, `TemplateAvailabilityProvider`s). Say precisely what moved and what
        did not. `[SOURCE]` `[VERSION-TRAP]` `[TRAP]`
3.10.19 `ConfigurationPropertiesBindingPostProcessor` + `ConfigurationPropertiesBinder` +
        `Binder` + `BindHandler` (`ValidationBindHandler`, `IgnoreErrorsBindHandler`) — the
        binding pipeline, including `BindResult` and the
        `ConfigurationPropertyName` normalisation that implements relaxed binding. `[SOURCE]`
3.10.20 `ConfigurationPropertyName` internals: elements, `UNIFORM` vs `DASHED` forms, and the
        `isValid` rules that reject uppercase in canonical names. This is relaxed binding's actual
        algorithm. `[SOURCE]` `[PROVE]` `[RESEARCH]`

*(20 leaves)*

## §3.11 AOT, native images, and build-time containers

3.11.1 The AOT thesis: move `refresh()`'s definition-phase work — configuration parsing, condition
       evaluation, scanning — to **build time**, emitting generated Java source that registers bean
       definitions directly. `[PROVE]`
3.11.2 `ApplicationContextAotGenerator`, `BeanFactoryInitializationAotProcessor`,
       `BeanRegistrationAotProcessor`, `BeanRegistrationAotContribution`,
       `GenerationContext`, `GeneratedFiles`, `RuntimeHints`. `[API]` `[SOURCE]`
3.11.3 What is generated: `<App>__ApplicationContextInitializer`, `<Bean>__BeanDefinitions`,
       `reflect-config.json`, `resource-config.json`, `proxy-config.json`,
       `native-image.properties`. `[NUM]` `[RESEARCH]`
3.11.4 `RuntimeHints` categories: `reflection()`, `resources()`, `serialization()`, `proxies()`,
       `reflection().registerType(..., MemberCategory...)`. `[API]`
3.11.5 `@ImportRuntimeHints(X.class)` + `RuntimeHintsRegistrar`, `@RegisterReflectionForBinding`,
       `@Reflective`. `[API]`
3.11.6 Running it: `mvn spring-boot:process-aot`, `-Dspring.aot.enabled=true` at runtime on the
       JVM, and `native-maven-plugin` / `bootBuildImage` for a native binary. `[NUM]`
3.11.7 The AOT limitations, stated as hard constraints: the classpath is fixed at build time;
       beans cannot change at runtime; `@Profile` and `@ConditionalOnProperty` that *change the
       bean set* are resolved at build time; `spring.main.lazy-initialization` is ignored;
       `@Bean` methods with conditional bodies are a problem. `[TRAP]` `[RESEARCH]`
3.11.8 A bean implementing `BeanRegistrationAotProcessor` is initialised **during AOT processing**
       along with all its dependencies — so only infrastructure beans should implement it.
       `[TRAP]` `[RESEARCH]`
3.11.9 CGLIB under AOT/native: proxy classes are generated at build time
       (`NativeDetector.inNativeImage()` in `DefaultAopProxyFactory`), and `@Configuration`
       full-mode classes get their enhanced subclass ahead of time. `[SOURCE]` `[PROVE]`
3.11.10 The AOT-vs-native distinction people conflate: AOT works on the plain JVM and cuts startup;
        native image additionally removes the JVM. Different costs, different failure modes.
        `[TRAP]` `[X-REF 06]`
3.11.11 Testing under AOT: `@EnabledIfRuntimeHintsAgent`, `RuntimeHintsPredicates`, and Spring's
        AOT test support (`spring.aot.enabled` in the test JVM). `[X-REF 16]`
3.11.12 CDS and Project Leyden as the non-AOT startup levers Boot 3.3+ supports
        (`-XX:ArchiveClassesAtExit`, `spring.context.exit=onRefresh`). `[X-REF 06]`
        `[RESEARCH]`
3.11.13 When AOT/native is worth it and when it is not: serverless and scale-to-zero yes;
        long-running services with dynamic classpaths no. `[X-REF 18]`

*(13 leaves)*

## §3.12 The TestContext framework internals

3.12.1 `TestContextManager`, `TestContext`, `TestExecutionListener`, `ContextLoader`,
       `SmartContextLoader`, `MergedContextConfiguration`, `ContextCache`,
       `DefaultCacheAwareContextLoaderDelegate`. `[API]` `[SOURCE]`
3.12.2 The cache key is the `MergedContextConfiguration`, built from **ten** components:
       `locations`, `classes`, `contextInitializerClasses`, `contextCustomizers`, `contextLoader`,
       `parent`, `activeProfiles`, `propertySourceDescriptors`, `propertySourceProperties`,
       `resourceBasePath`. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.12.3 `ContextCustomizer` sources that silently change the key: `@DynamicPropertySource`,
       every bean override (`@MockitoBean`, `@MockitoSpyBean`, `@TestBean`), Boot's
       `ExcludeFilterContextCustomizer`, `DuplicateJsonObjectContextCustomizer`,
       `MockWebServiceServerContextCustomizer`, `PropertyMappingContextCustomizer`. `[SOURCE]`
       `[RESEARCH]`
3.12.4 Default cache size **32**, LRU eviction, configured by the
       `spring.test.context.cache.maxSize` JVM property or `SpringProperties`. `[NUM]`
       `[PROP]` `[RESEARCH]`
3.12.5 The cache is a **static** field, so forking per test class (Surefire `forkMode`,
       Gradle `forkEvery`) disables it entirely. `[TRAP]` `[RESEARCH]`
3.12.6 Cache statistics: set `org.springframework.test.context.cache` to DEBUG to get
       `size`, `maxSize`, `parentContextCount`, `hitCount`, `missCount`. Use it to measure
       context forking in a slow suite. `[DIAG]` `[RESEARCH]`
3.12.7 `@DirtiesContext` modes and `DirtiesContextBeforeModesTestExecutionListener` /
       `DirtiesContextTestExecutionListener`. `[API]`
3.12.8 The default `TestExecutionListener` set, in order:
       `ServletTestExecutionListener`, `DirtiesContextBeforeModesTestExecutionListener`,
       `ApplicationEventsTestExecutionListener`, `BeanOverrideTestExecutionListener`,
       `DependencyInjectionTestExecutionListener`, `MicrometerObservationRegistryTestExecutionListener`,
       `DirtiesContextTestExecutionListener`, `CommonCachesTestExecutionListener`,
       `TransactionalTestExecutionListener`, `SqlScriptsTestExecutionListener`,
       `EventPublishingTestExecutionListener`. `[SOURCE]` `[RESEARCH]`
3.12.9 `TransactionalTestExecutionListener` — the listener that starts a transaction before each
       test method and rolls it back after, and `TestTransaction` for manual control. `[SOURCE]`
3.12.10 Boot's `SpringBootTestContextBootstrapper`, `SpringBootContextLoader`, and how a slice
        annotation (`@WebMvcTest`) narrows auto-configuration via `TypeExcludeFilter` +
        `AutoConfigureWebMvc` + `spring.factories` slice metadata. `[SOURCE]` `[X-REF 16]`
3.12.11 Practical consequences: sort your test classes into a small number of context shapes; put
        `@MockitoBean` in a shared base class; prefer `@TestConfiguration` over per-test property
        overrides. `[PROVE]` `[X-REF 16]`

*(11 leaves)*

## §3.13 The Boot loader and packaging internals

3.13.1 `JarLauncher` → `Archive` / `NestedJarFile` → `LaunchedClassLoader` → reflective call to
       `Start-Class.main`. `[SOURCE]`
3.13.2 The Boot 3.2 loader rewrite (`org.springframework.boot.loader.launch`) and the removal of
       the old `LaunchedURLClassLoader` name. `[VERSION-TRAP]` `[RESEARCH]`
3.13.3 Nested jars are stored **uncompressed** (`STORED`) so entries can be read in place; this is
       why a Boot fat jar is larger than the sum of its dependencies. `[NUM]` `[PROVE]`
3.13.4 `MANIFEST.MF` keys: `Main-Class`, `Start-Class`, `Spring-Boot-Version`,
       `Spring-Boot-Classes`, `Spring-Boot-Lib`, `Spring-Boot-Classpath-Index`,
       `Spring-Boot-Layers-Index`. `[NUM]` `[SOURCE]`
3.13.5 `layers.idx` and `java -Djarmode=tools extract --layers` (Boot 3.3+; previously
       `-Djarmode=layertools`). `[VERSION-TRAP]` `[X-REF 19]`
3.13.6 `PropertiesLauncher` and `loader.path` for external configuration/plugin directories.
3.13.7 `build-info.properties` / `git.properties` and the actuator `info` endpoint.
3.13.8 Why `getResource().getFile()` fails from a fat jar, restated at the loader level.
       `[TRAP]` `[X-REF §1.19.5]`
3.13.9 The WAR path: `SpringBootServletInitializer`, `war` packaging,
       `provided` scope for the embedded container, and when you still need it. `[VERSION-TRAP]`

*(9 leaves)*

## §3.14 Failure modes, read at source level

3.14.1 The container-failure decision tree: does the context start? → does the bean exist? → is it
       the right instance? → is it advised? → did the advice fire? Each branch names the
       diagnostic. `[FLOW]` `[DIAG]`
3.14.2 `UnsatisfiedDependencyException` full trace anatomy: outer bean, injection point,
       inner cause, and the "Consider defining a bean of type X" Boot action block. `[DIAG]`
3.14.3 `NoUniqueBeanDefinitionException` listing all candidates — and the three fixes in the Boot
       action text. `[DIAG]`
3.14.4 `BeanCurrentlyInCreationException` and the circular-reference ASCII box. `[DIAG]`
3.14.5 `ApplicationContextException: Unable to start web server` → `BindException: Address already
       in use` chain. `[DIAG]` `[X-REF 10]`
3.14.6 `ConfigurationPropertiesBindException` with the nested `BindValidationException` field list.
       `[DIAG]`
3.14.7 `Cannot subclass final class` / `Could not generate CGLIB subclass` — and the
       `IllegalArgumentException: Superclass has no null constructors but no arguments were given`
       when Objenesis is unavailable. `[DIAG]`
3.14.8 `IllegalStateException: No thread-bound request found: Are you referring to request
       attributes outside of an actual web request...` — read the whole message, it names the fix.
       `[DIAG]`
3.14.9 `UnexpectedRollbackException: Transaction silently rolled back because it has been marked as
       rollback-only`. `[DIAG]`
3.14.10 `No qualifying bean of type 'javax.sql.DataSource'` + "Failed to configure a DataSource: no
        embedded datasource could be auto-configured" — the most-seen Boot failure and its four
        causes. `[DIAG]`
3.14.11 A silent failure catalogue — the ones that produce **no** error at all: self-invocation,
        `private`/`final` annotated methods, `@Async` swallowed exceptions, checked-exception
        commit, a `@Scheduled` method whose exception killed the only scheduler thread, a
        `@ConditionalOnProperty` typo, a component outside the scanned package, `@Value` on a
        non-bean, a `@Transactional` test that always rolls back. `[TRAP]`
3.14.12 Memory and the container: proxy classes in metaspace, `ThreadLocal`-bound transaction
        resources on a leaked thread, a `@Scheduled`-populated static cache, and a context that is
        never closed in tests. `[X-REF 06]` `[X-REF 05]`

*(12 leaves)*

---

**PART 3 total: 20+16+16+14+15+10+19+20+15+20+13+11+9+12 = 210 leaves**

---

# PART 4 — BUILD IT

Every `[BUILD]` leaf ships complete, compiling Java 21 (no `...` elisions, no pseudo-code) and is
followed by a **Diff vs the real one** table covering at minimum: thread safety, caching, error
messages, ordering, extension points, generics/`ResolvableType`, AOT, and why the real
implementation bothers.

## §4.1 A minimal IoC container

4.1.1 `MiniBeanDefinition` as a record: `Class<?> type`, `String scope`, `boolean lazy`,
      `Constructor<?> constructor`, `List<String> dependsOn`, `String initMethod`,
      `String destroyMethod`. `[BUILD]`
4.1.2 `MiniBeanFactory` with `Map<String, MiniBeanDefinition>` + `Map<String, Object>` singleton
      cache and `getBean(String)` / `getBean(Class<T>)`. `[BUILD]`
4.1.3 Constructor-based instantiation with recursive dependency resolution and cycle detection via
      a creation set. `[BUILD]`
4.1.4 Prototype scope, and the deliberate decision **not** to track prototypes for destruction —
      mirroring Spring exactly. `[BUILD]`
4.1.5 Lifecycle: `@PostConstruct` / `@PreDestroy` discovery by reflection, plus a `close()` that
      destroys in reverse registration order. `[BUILD]`
4.1.6 Diff vs `DefaultListableBeanFactory`: merged definitions, `FactoryBean`, aliases, parent
      factories, the three-level cache, `ResolvableType` generics, definition freezing,
      `ApplicationStartup`, the whole `BeanPostProcessor` SPI.

*(6 leaves)*

## §4.2 Annotation scanning and injection

4.2.1 `@MiniComponent`, `@MiniAutowired`, `@MiniQualifier`, `@MiniValue`, `@MiniPrimary` as
      runtime-retained annotations. `[BUILD]`
4.2.2 A classpath scanner over a base package using `ClassLoader.getResources` and directory/jar
      walking, without loading every class eagerly where avoidable. `[BUILD]`
4.2.3 Constructor selection implementing the real four-rule algorithm from §1.6.3, including the
      "greediest satisfiable" branch. `[BUILD]`
4.2.4 Field and setter injection with `setAccessible(true)`, and a switch that turns field
      injection off so the reader can *watch* a cycle start failing. `[BUILD]` `[PROVE]`
4.2.5 Candidate resolution: qualifier → primary → parameter-name match →
      `MiniNoUniqueBeanException` with all candidates listed. `[BUILD]`
4.2.6 `List<T>` and `Map<String,T>` injection with `@MiniOrder` sorting. `[BUILD]`
4.2.7 Diff vs `AutowiredAnnotationBeanPostProcessor` + `DefaultListableBeanFactory`:
      `InjectionMetadata` caching, ASM metadata reading, `@Fallback`/`@Priority`, generics,
      `ObjectProvider`, JSR-330, meta-annotation merging, error-message quality.

*(7 leaves)*

## §4.3 The three-level cache, built and proved

4.3.1 Add `earlySingletonObjects` and `singletonFactories` to `MiniBeanFactory` and implement
      `getSingleton(name, allowEarlyReference)` with the exact three-level logic. `[BUILD]`
4.3.2 `addSingletonFactory` at the right point in creation, and a `beforeSingletonCreation` /
      `afterSingletonCreation` pair. `[BUILD]`
4.3.3 A test that a setter cycle resolves and a constructor cycle throws, with printed trace lines
      showing which cache level served each lookup. `[BUILD]` `[PROVE]`
4.3.4 Add a `getEarlyBeanReference` hook and a toy proxy creator, then demonstrate the
      "injected in raw version but eventually wrapped" failure and how the L3 factory fixes it.
      `[BUILD]` `[PROVE]`
4.3.5 Collapse to two levels and show precisely what breaks — the empirical proof for §3.4.6.
      `[BUILD]` `[PROVE]`
4.3.6 Diff vs `DefaultSingletonBeanRegistry`: concurrency, lenient creation locks, dependent-bean
      graph, suppressed exceptions, `inCreationCheckExclusions`.

*(6 leaves)*

## §4.4 A JDK-dynamic-proxy AOP framework

4.4.1 `MiniPointcut` (`ClassFilter` + `MethodMatcher`), `MiniAdvice`
      (an AOP-Alliance-shaped `MethodInterceptor`), `MiniAdvisor`. `[BUILD]`
4.4.2 `MiniProxyFactory.getProxy()` using `Proxy.newProxyInstance` and an `InvocationHandler`.
      `[BUILD]`
4.4.3 `MiniMethodInvocation.proceed()` — the recursive chain with an interceptor index, mirroring
      `ReflectiveMethodInvocation`. `[BUILD]`
4.4.4 Before / after-returning / after-throwing / around advice implemented on top of the single
      interceptor primitive, proving that one primitive suffices. `[BUILD]` `[PROVE]`
4.4.5 An annotation-driven pointcut (`@MiniLogged`) and advisor ordering by `@MiniOrder`.
      `[BUILD]`
4.4.6 Wire it into `MiniBeanFactory` as a post-initialization step so beans come out proxied.
      `[BUILD]`
4.4.7 Demonstrate self-invocation failing inside the mini framework — the same bug, in fifty lines.
      `[BUILD]` `[PROVE]` `[TRAP]`
4.4.8 Diff vs `JdkDynamicAopProxy` + `AdvisedSupport`: `equals`/`hashCode`/`Advised` routing,
      `ExposeInvocationInterceptor`, the method cache, dynamic method matchers, `TargetSource`,
      introductions, serialization, `DecoratingProxy`.

*(8 leaves)*

## §4.5 A subclass proxy without an interface

4.5.1 The same framework via Byte Buddy (or `java.lang.reflect.Proxy`'s limitation stated and then
      worked around) producing a subclass proxy. `[BUILD]`
4.5.2 Show that `final` methods are not overridden and therefore not advised — reproduce the trap
      in code. `[BUILD]` `[PROVE]` `[TRAP]`
4.5.3 Show the constructor running on the subclass, then avoid it with `Objenesis`-style
      allocation, and print the field state on proxy vs target. `[BUILD]` `[PROVE]`
4.5.4 Diff vs `CglibAopProxy`: the seven-callback filter, `MethodProxy` fast invocation,
      `SpringNamingPolicy`, classloader/`ClassLoaderAwareGeneratorStrategy`, native-image support.

*(4 leaves)*

## §4.6 A `@MiniTransactional` interceptor

4.6.1 A `MiniTransactionManager` over a `DataSource` with a `ThreadLocal<ConnectionHolder>`,
      `begin`, `commit`, `rollback`, `suspend`, `resume`. `[BUILD]`
4.6.2 `MiniTransactionInterceptor` implementing `REQUIRED`, `REQUIRES_NEW`, `MANDATORY`, `NEVER`,
      `SUPPORTS`, `NOT_SUPPORTED` and `NESTED` (JDBC savepoints). `[BUILD]`
4.6.3 The default rollback rule (`RuntimeException`/`Error` only) plus `rollbackFor`, with the
      depth-scoring rule implemented. `[BUILD]` `[PROVE]`
4.6.4 `setRollbackOnly` and reproducing `UnexpectedRollbackException` end to end. `[BUILD]`
      `[PROVE]` `[TRAP]`
4.6.5 A `MiniTransactionSynchronization` registry and a `MiniTransactionalEventListener` firing
      `AFTER_COMMIT` — the two mechanisms joined. `[BUILD]`
4.6.6 A test with H2 (or an in-memory fake `DataSource`) proving each propagation's commit
      behaviour with row counts. `[BUILD]`
4.6.7 Diff vs `TransactionInterceptor` + `AbstractPlatformTransactionManager`: attribute caching,
      `TransactionAttributeSource` search order, isolation/timeout/read-only, JPA/JTA managers,
      reactive support, `globalRollbackOnParticipationFailure`, synchronization ordering.

*(7 leaves)*

## §4.7 A mini auto-configuration mechanism

4.7.1 A `MiniCondition` SPI plus `@MiniConditionalOnClass`, `@MiniConditionalOnMissingBean`,
      `@MiniConditionalOnProperty(matchIfMissing)`. `[BUILD]`
4.7.2 A `META-INF/mini/AutoConfiguration.imports`-style resource loader that reads candidates from
      every jar on the classpath. `[BUILD]`
4.7.3 Deferred processing: register user configuration first, auto-configuration second, and prove
      that back-off only works in that order. `[BUILD]` `[PROVE]`
4.7.4 A conditions-evaluation report printer with positive/negative matches and reasons. `[BUILD]`
      `[DIAG]`
4.7.5 A worked "mini starter": a `MiniHttpClientAutoConfiguration` that backs off when the user
      defines their own client. `[BUILD]`
4.7.6 Diff vs `AutoConfigurationImportSelector`: the metadata pre-filter, the three-stage sorter,
      `@AutoConfigureBefore/After`, exclusion handling, AOT contribution, the real report model.

*(6 leaves)*

## §4.8 A relaxed-binding property binder

4.8.1 A `MiniPropertyName` type implementing the canonical/kebab/camel/underscore/env-var
      equivalence, with an `equals`/`hashCode` that makes all forms the same key. `[BUILD]`
      `[PROVE]`
4.8.2 An ordered `MiniPropertySource` list with first-wins resolution and a `getPropertyOrigin`
      that reports which source won. `[BUILD]` `[DIAG]`
4.8.3 `${a.b:default}` placeholder resolution with recursion and cycle detection. `[BUILD]`
4.8.4 Binding to a `record` by constructor with `Duration`/`DataSize`/enum/`List`/nested-record
      conversion. `[BUILD]`
4.8.5 Validation with Jakarta Validation and a startup failure report listing every violated field.
      `[BUILD]`
4.8.6 Diff vs `Binder` + `ConfigurationPropertyName` + `Environment`: `BindHandler`s, origin
      tracking, map/indexed binding, `@DefaultValue`, `@Name`, `ConversionService` integration,
      config-data contributor tree.

*(6 leaves)*

## §4.9 A mini event multicaster

4.9.1 `MiniEventPublisher` with generic-aware listener matching using
      `ParameterizedType`. `[BUILD]`
4.9.2 `@MiniEventListener` discovery after all singletons exist (a `SmartInitializingSingleton`
      analogue), and the demonstration that lazy beans are missed. `[BUILD]` `[PROVE]`
4.9.3 Synchronous by default; an executor-backed async mode; an error handler; ordering.
      `[BUILD]`
4.9.4 Transaction-phase listeners hooked to §4.6's synchronization registry. `[BUILD]`
4.9.5 Diff vs `SimpleApplicationEventMulticaster` + `ApplicationListenerMethodAdapter`: retriever
      caching, `ResolvableType`, SpEL conditions, `PayloadApplicationEvent`, returned-event
      republication, early events.

*(5 leaves)*

## §4.10 Diagnostics you write yourself

4.10.1 A `BeanFactoryPostProcessor` that prints every definition with scope, class, and source, and
       flags definitions overridden more than once. `[BUILD]`
4.10.2 A `BeanPostProcessor` that fails startup when a `private`, `final` or `static` method carries
       `@Transactional`, `@Async`, `@Cacheable` or `@PreAuthorize`. `[BUILD]` `[TRAP]`
4.10.3 A startup timer: a `BeanPostProcessor` recording per-bean initialisation time and printing
       the slowest twenty. `[BUILD]` `[X-REF 20]`
4.10.4 A proxy inspector: for every bean, print whether it is a proxy, which kind, and the ordered
       advisor list from `Advised`. `[BUILD]` `[DIAG]`
4.10.5 An ArchUnit rule set: no field injection, no `@Transactional` on `@Repository`, no
       `ApplicationContextAware` outside infrastructure, no entity return types on controllers.
       `[BUILD]` `[X-REF 16]`
4.10.6 A test that fails when the Spring context cache forks more than N times across the suite.
       `[BUILD]` `[X-REF 16]`
4.10.7 A `SmartLifecycle` bean that logs phase transitions so shutdown ordering becomes visible.
       `[BUILD]` `[DIAG]`

*(7 leaves)*

---

**PART 4 total: 6+7+6+8+4+7+6+6+5+7 = 62 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The question set, with the answer shape

Each leaf is one question plus the two-to-four sentence shape of a strong answer, plus the
follow-up the interviewer will ask if you answer well.

**Container fundamentals**

5.1.1 What is inversion of control, and what specifically is inverted?
5.1.2 What is a bean? (Correct answer starts with `BeanDefinition`, not "an object Spring makes".)
5.1.3 `BeanFactory` versus `ApplicationContext` — six differences.
5.1.4 Walk the bean lifecycle in exact order.
5.1.5 `BeanFactoryPostProcessor` versus `BeanPostProcessor` — which phase, which argument, one real
      example of each.
5.1.6 Where in the lifecycle is the AOP proxy created, and what does that imply for
      `@PostConstruct`?
5.1.7 Why does a `BeanPostProcessor`'s own dependency not get proxied?
5.1.8 What does `@Primary` do that `@Qualifier` does not?
5.1.9 What is `@Fallback` and when would you use it over `@Primary`?
5.1.10 Constructor versus field injection — give four arguments, not one.
5.1.11 How does Spring choose a constructor when there are three?
5.1.12 What does `@Autowired(required=false)` do to a method versus a field?
5.1.13 What is `ObjectProvider` and name three problems it solves.
5.1.14 What is `@Lookup` and how is it implemented?
5.1.15 What happens if you inject `List<Validator>`? How is the order decided?
5.1.16 What does `@Order` affect, and what does it explicitly not affect?
5.1.17 Which stereotype annotations have real behaviour, and what is it?
5.1.18 What is a `FactoryBean` and what does `&` do?
5.1.19 What does `@DependsOn` do that injection does not?
5.1.20 What does `spring.main.lazy-initialization=true` cost you?

**Scopes**

5.1.21 Singleton means one per what?
5.1.22 Why is a mutable field on a `@Service` a bug?
5.1.23 What happens when you inject a prototype into a singleton, and name three fixes.
5.1.24 Is `@PreDestroy` called on a prototype? Why not?
5.1.25 How does a request-scoped bean get injected into a singleton?
5.1.26 What is `ScopedProxyMode.TARGET_CLASS` doing mechanically?
5.1.27 Why does accessing a request-scoped bean from `@Async` throw?
5.1.28 Implement a custom scope — what four methods?

**Proxies and AOP**

5.1.29 State the proxy model in one sentence.
5.1.30 JDK dynamic proxy versus CGLIB — five differences and what Boot defaults to.
5.1.31 Why does `@Transactional` on a private method do nothing, with no error?
5.1.32 Explain self-invocation and rank the fixes.
5.1.33 Which other annotations have the same limitation?
5.1.34 What happens if the class is `final`? What if it is a record?
5.1.35 Can you proxy a bean and have two advisors? How are they ordered?
5.1.36 What is `ProceedingJoinPoint.proceed()` actually doing? (Answer:
       `ReflectiveMethodInvocation.proceed()` with an index.)
5.1.37 Which AspectJ pointcut designators does Spring AOP support, and what is the one join-point
       type it supports?
5.1.38 `this()` versus `target()` in a pointcut.
5.1.39 How would you verify at runtime that a bean is proxied?
5.1.40 Why do `@Configuration` classes get CGLIB-enhanced, and what does
       `proxyBeanMethods=false` give up?

**Transactions**

5.1.41 What does `@Transactional` actually do at runtime, step by step?
5.1.42 How does a repository three layers down know it is in a transaction?
5.1.43 Name all seven propagations and what `REQUIRES_NEW` costs.
5.1.44 `REQUIRES_NEW` versus `NESTED`.
5.1.45 What is the default rollback rule and why is it that way?
5.1.46 Explain `UnexpectedRollbackException`.
5.1.47 What does `readOnly = true` actually do — three effects.
5.1.48 Where should `@Transactional` go, and why not on the interface?
5.1.49 Your `@Transactional` method calls an HTTP API that takes 8 seconds. What is wrong?
5.1.50 How would you write an audit row that survives a rollback? Four options, compare.
5.1.51 What is `TransactionSynchronizationManager` and what does it hold?
5.1.52 Why does a constraint violation surface at commit rather than at the `save()` call?
5.1.53 Two transaction managers in one app — how does Spring pick?

**Events**

5.1.54 Is `@EventListener` synchronous? What happens if it throws?
5.1.55 When do you use `@TransactionalEventListener(AFTER_COMMIT)`?
5.1.56 Why does a DB write inside an `AFTER_COMMIT` listener silently do nothing?
5.1.57 Why can't an `@EventListener` bean observe `ApplicationStartingEvent`?
5.1.58 What is `ContextRefreshedEvent` and why might it fire twice?
5.1.59 Events versus a message broker — when does each win?

**Boot and configuration**

5.1.60 What are the three annotations inside `@SpringBootApplication`?
5.1.61 Explain auto-configuration end to end.
5.1.62 Where does the candidate list come from? (And what did it used to be?)
5.1.63 Why do user beans win over auto-configured ones?
5.1.64 Why is `@ConditionalOnMissingBean` only reliable inside auto-configuration?
5.1.65 What does a starter actually contain?
5.1.66 How do you find out why a bean was not created?
5.1.67 Name the top five property sources in precedence order.
5.1.68 Why does an environment variable beat `application.yml`?
5.1.69 `@Value` versus `@ConfigurationProperties` — five reasons.
5.1.70 What is relaxed binding, and does `@Value` get it?
5.1.71 How do you validate configuration at startup?
5.1.72 What changed about `@ConstructorBinding` in Boot 3?
5.1.73 What are profiles for, and what are they not for?
5.1.74 How do you get secrets into a Boot app in Kubernetes?
5.1.75 What does `spring.config.import` do?

**Web layer**

5.1.76 Walk a request from socket to controller and back.
5.1.77 Filter versus interceptor versus aspect.
5.1.78 Why doesn't a Spring Security 403 hit your `@ControllerAdvice`?
5.1.79 Why should you not return a JPA entity from a controller?
5.1.80 `MethodArgumentNotValidException` versus `ConstraintViolationException`.
5.1.81 What happens if you add `@EnableWebMvc` to a Boot app?
5.1.82 How does `@RestControllerAdvice` pick a handler when two match?

**Async and scheduling**

5.1.83 What thread does `@Async` run on by default in Boot 3.5?
5.1.84 Why did your `@Async` method's exception disappear?
5.1.85 How many threads does `@Scheduled` use by default?
5.1.86 `fixedRate` versus `fixedDelay`.
5.1.87 Your nightly job ran three times. Why, and name three fixes.
5.1.88 Does the security context propagate into `@Async`?

**Internals**

5.1.89 What are the three levels of the singleton cache and why three?
5.1.90 Walk a field-injection circular dependency through the caches.
5.1.91 Why can a constructor cycle never be resolved?
5.1.92 Are circular references allowed by default? Since when?
5.1.93 Name the twelve steps of `refresh()`.
5.1.94 What runs in `invokeBeanFactoryPostProcessors` and in what order?
5.1.95 What is `ConfigurationClassPostProcessor` and why must it be `PriorityOrdered`?
5.1.96 What does `DeferredImportSelector` buy auto-configuration?
5.1.97 How does `getEarlyBeanReference` interact with AOP?
5.1.98 Why does `@Async` on a bean in a cycle fail when `@Transactional` does not?
5.1.99 What does `freezeConfiguration()` optimise?
5.1.100 Is the Spring container thread-safe? Are your beans?

**Design and Staff-level**

5.1.101 You inherit a service with 40 `@Autowired` fields on one class. What do you do, in order?
5.1.102 A team wants to enable `spring.main.allow-circular-references=true` to ship. Argue.
5.1.103 Your test suite takes 22 minutes and starts 60 contexts. Diagnose and fix.
5.1.104 Startup takes 45 seconds and Kubernetes kills the pod. Name five levers with their costs.
5.1.105 Design a plugin system where third parties add strategies via a jar drop.
5.1.106 When would you *not* use Spring for a new service?
5.1.107 How do you keep a shared internal starter from becoming a coupling disaster?
5.1.108 Would you adopt GraalVM native for this service? Argue both sides.
5.1.109 How do you enforce the traps in this guide at build time rather than review time?
5.1.110 Explain the container to a new grad in five minutes without saying "magic".

*(110 leaves)*

## §5.2 The trap index

One line each: the wrong belief, the symptom, the fix. Read this before every interview.

5.2.1 "Field injection is fine." → untestable, hides cycles → constructor injection.
5.2.2 "`@Service` does something." → nothing → only `@Repository` has behaviour.
5.2.3 "Swapping `@Repository` for `@Component` is harmless." → loses exception translation.
5.2.4 "Singleton means one per JVM." → one per container.
5.2.5 A mutable field on a singleton → cross-request data corruption under load.
5.2.6 Prototype injected into singleton → one instance forever.
5.2.7 `@PreDestroy` on a prototype → never called.
5.2.8 `@Transactional` on a private method → silently ignored.
5.2.9 `@Transactional` on a `final` method or `final` class → silently ignored / startup failure.
5.2.10 `this.transactionalMethod()` → no transaction.
5.2.11 `this.cacheableMethod()` → cache never consulted.
5.2.12 `this.asyncMethod()` → runs on the caller thread.
5.2.13 `@Transactional` called from `@PostConstruct` → no transaction, proxy does not exist yet.
5.2.14 Checked exception thrown from a `@Transactional` method → **commits**.
5.2.15 Catching an exception inside an inner `REQUIRED` method → `UnexpectedRollbackException`.
5.2.16 Catching inside the same transactional method → partial work commits.
5.2.17 `REQUIRES_NEW` for an audit row → second connection, pool pressure, possible deadlock.
5.2.18 `readOnly=true` on a class with write methods → updates silently lost.
5.2.19 `@Transactional` on the repository → transaction boundary in the wrong layer.
5.2.20 `@Transactional` spanning an HTTP call → connection held for the remote timeout.
5.2.21 `@Transactional` on an interface method with CGLIB → not applied.
5.2.22 Constraint violation appears at commit, not at `save()` → cannot be caught inside.
5.2.23 `@EventListener` is asynchronous → it is not; it can roll your transaction back.
5.2.24 DB write in an `AFTER_COMMIT` listener → no transaction; needs `REQUIRES_NEW`.
5.2.25 `@TransactionalEventListener` outside a transaction → listener silently skipped.
5.2.26 `@EventListener` on a `@Lazy` bean → never registered.
5.2.27 `@EventListener` for `ApplicationStartingEvent` → too late to be registered.
5.2.28 `ContextRefreshedEvent` firing twice in a classic MVC app → startup work runs twice.
5.2.29 `@Async` void method → exceptions swallowed.
5.2.30 `@Async` default executor unbounded queue → memory growth, `max-size` never reached.
5.2.31 `@Async` does not carry MDC / security context / request scope / transaction.
5.2.32 Boot 3.5 removed the `taskExecutor` bean alias → `@Qualifier("taskExecutor")` breaks.
5.2.33 `@Scheduled` default pool size 1 → jobs queue behind each other.
5.2.34 `@Scheduled` on every replica → job runs N times.
5.2.35 Spring cron has six fields, not five.
5.2.36 `fixedRate` with a slow job → overlapping or bursting executions.
5.2.37 Virtual threads + no keep-alive → JVM exits before the scheduler runs.
5.2.38 Main class in a leaf package → components not scanned.
5.2.39 `@ComponentScan(useDefaultFilters=false)` → nothing is found.
5.2.40 Two beans with the same simple name in different packages → override or conflict.
5.2.41 `spring.factories` for auto-configuration → removed in Boot 3.0.
5.2.42 `@ConditionalOnMissingBean` on an interface return type → back-off misses.
5.2.43 `@ConditionalOnBean` in user configuration → order-dependent, unreliable.
5.2.44 `@ConditionalOnProperty` without `matchIfMissing=true` → feature off by default.
5.2.45 Boot 3.5: `.enabled=yes` no longer means true.
5.2.46 `@EnableWebMvc` in a Boot app → disables all MVC auto-configuration.
5.2.47 Returning a JPA entity from a controller → `LazyInitializationException` mid-response.
5.2.48 `@Valid` on a service parameter throws a different exception than on a controller.
5.2.49 Stale environment variable outranks the yml you just edited.
5.2.50 `@Value` does not get relaxed binding.
5.2.51 `@Value` on a static field → permanently null.
5.2.52 `@Autowired` on a static field → permanently null.
5.2.53 `resource.getFile()` inside a fat jar → `FileNotFoundException`.
5.2.54 `@PropertySource` does not read YAML.
5.2.55 `@ConstructorBinding` on the type in Boot 3 → no longer valid.
5.2.56 `new MyService()` inside another bean → no injection, no advice.
5.2.57 `@Configuration(proxyBeanMethods=false)` + inter-method call → two instances.
5.2.58 A `BeanPostProcessor`'s dependencies are not eligible for post-processing.
5.2.59 `@Autowired` inside a `BeanPostProcessor` → not injected.
5.2.60 `PropertySourcesPlaceholderConfigurer` as a non-static `@Bean` → too late.
5.2.61 Circular references are disabled by default since Boot 2.6.
5.2.62 `allow-circular-references=true` treated as a fix.
5.2.63 `@Async` bean in a circular dependency → wrapping check fails startup.
5.2.64 `@MockitoBean` in one test → a whole extra application context.
5.2.65 Forking per test class → context cache disabled entirely.
5.2.66 `@Transactional` test → rolls back, so `AFTER_COMMIT` listeners never fire.
5.2.67 `@DirtiesContext` sprinkled everywhere → suite time explodes.
5.2.68 Records cannot be CGLIB-proxied — they are `final`.
5.2.69 Kotlin classes are `final` by default → need the `allopen` plugin.
5.2.70 Reading state off a CGLIB proxy's fields → defaults, not the target's values.
5.2.71 Side effects in a proxied bean's constructor → run twice or not at all.
5.2.72 `SimpleThreadScope` never runs destruction callbacks.
5.2.73 `@Order` assumed to control startup order → it does not.
5.2.74 `@Priority` on a `@Bean` method → not supported.
5.2.75 Profiles used to store secrets or environment URLs in git.
5.2.76 `spring.profiles.active` set in `application.yml` → ignored in some layers; set it outside.
5.2.77 `@Profile` on an `@Import`ed class → phase confusion.
5.2.78 SpEL evaluated on user input with `StandardEvaluationContext` → RCE.
5.2.79 `@Cacheable` `unless` versus `condition` confusion → wrong entries cached.
5.2.80 `SimpleKeyGenerator` collisions between two methods sharing a cache name.
5.2.81 Lazy initialization in production without warmup → first-request latency and late failures.
5.2.82 AOT/native + `@Profile`-varying bean sets → the profile is baked in at build time.
5.2.83 Assuming the container makes your beans thread-safe.
5.2.84 `getBean()` sprinkled through application code → service locator regression.

*(84 leaves)*

## §5.3 One-line assertions and drills

5.3.1 The 30-second container story: definitions → BFPPs → BPPs → instantiate → wire → initialise →
      proxy → in use → destroy.
5.3.2 The 30-second proxy story: the context holds a proxy; interceptors run around your method;
      `this` skips them.
5.3.3 The 30-second transaction story: the interceptor binds a connection to the thread and commits
      on normal return, rolls back on unchecked exceptions.
5.3.4 The 30-second auto-configuration story: a deferred import selector reads
      `AutoConfiguration.imports`, filters by conditions, registers after your beans.
5.3.5 **Numbers drill** — recite from memory: `singletonObjects` capacity 256, context cache size
      32, scheduler pool size 1, task executor core size 8, Tomcat max threads 200,
      `Ordered.HIGHEST_PRECEDENCE` = `Integer.MIN_VALUE`, `timeoutPerShutdownPhase` 30 s,
      transaction timeout default −1, `ROLE_INFRASTRUCTURE` = 2, cron fields = 6, property sources
      = 15. `[NUM]`
5.3.6 **Class-name drill** — for each behaviour, name the class:
      creates AOP proxies, parses `@Configuration`, injects `@Autowired`, invokes
      `@PostConstruct`, registers `@EventListener`, binds `@ConfigurationProperties`,
      intercepts `@Transactional`, holds the connection, selects auto-configurations,
      resolves placeholders, caches test contexts.
5.3.7 **Ordering drill** — put in order: `@PostConstruct`, `afterPropertiesSet`, `initMethod`,
      `postProcessBeforeInitialization`, `postProcessAfterInitialization`, constructor injection,
      field injection, `Aware` callbacks, `SmartInitializingSingleton`, `ApplicationRunner`.
5.3.8 **Diagnosis drill** — for each of ten symptoms, name the first command or log category you
      would run. `[DIAG]`
5.3.9 **Version drill** — for each of fifteen claims, say whether it is true in Boot 3.5 and what
      changed. `[VERSION-TRAP]`
5.3.10 **Whiteboard drill** — draw `refresh()` as twelve boxes and the three-level cache as three,
       from memory, in under three minutes.
5.3.11 **Code-review drill** — a 60-line service class with nine planted bugs from §5.2; find them
       all in ten minutes.
5.3.12 Spaced repetition plan: §5.2 daily, §5.1 by block weekly, PART 3 once before the onsite.
5.3.13 The two-minute answer template for any "why doesn't my annotation work" question: is it a
       bean → is the call through the proxy → is the method advisable → is the feature enabled →
       what does the conditions report say.

*(13 leaves)*

---

**PART 5 total: 110+84+13 = 207 leaves**

---

## Sources consulted

Primary sources first. Where a fetch failed or a search returned nothing usable, that is stated
rather than padded. Every `[RESEARCH]` leaf must be re-verified against the source named here
before the write pass commits a constant, a default or an API shape to the page.

**Spring Framework reference documentation (primary)**

- <https://docs.spring.io/spring-framework/reference/core/beans/factory-nature.html> — fetched in
  full. Source of the complete `Aware` interface table (§1.9.2), the initialisation/destruction
  ordering rule `@PostConstruct` → `afterPropertiesSet` → custom init (§1.9.5), `Lifecycle` /
  `SmartLifecycle` / `Phased` / `LifecycleProcessor` signatures, the phase semantics
  (lowest starts first, stops last; default 0), `DefaultLifecycleProcessor` bean name
  `lifecycleProcessor` with a **30-second** default `timeoutPerShutdownPhase`, and
  `SmartInitializingSingleton.afterSingletonsInstantiated()`. Basis of §1.9.
- <https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html> —
  fetched in full. Source of the constructor-detection rules (§1.6.3), `required` semantics for
  methods versus fields (§1.6.8), `Optional`/`@Nullable` including JSpecify acceptance,
  the `ObjectProvider` method list, array/collection/`Map` injection, the `@Order`-does-not-affect-
  startup-order rule (§1.7.11), `@Priority` not being available on `@Bean` methods, the
  well-known resolvable dependencies list (§1.6.18), self-injection as lowest-precedence fallback
  (§1.6.19), and the "cannot use `@Autowired` in a `BeanPostProcessor`" restriction (§1.6.20).
- <https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html> — fetched in
  full. Source of the six built-in scopes plus unregistered `thread`, the `Scope` SPI's four
  methods, `ScopedProxyMode` behaviour, `RequestContextListener` / `RequestContextFilter`,
  `registerScope` / `CustomScopeConfigurer`, `SimpleThreadScope`, and the per-scope destruction
  table including "prototype: not called". Basis of §1.8.
- <https://docs.spring.io/spring-framework/reference/core/beans/environment.html> — fetched in
  full. Source of `MutablePropertySources`' six mutation methods, the `StandardEnvironment` source
  names `systemProperties` and `systemEnvironment` with system properties winning, the
  `StandardServletEnvironment` five-source order, profile expression operators and the
  parentheses rule, `spring.profiles.active` / `spring.profiles.default`, `@PropertySource`
  including placeholders and repeatability, and the "only the first `@Profile` declaration on
  overloaded `@Bean` methods matters" note (§1.11.12). Basis of §1.16.
- <https://docs.spring.io/spring-framework/reference/core/beans/context-introduction.html> —
  fetched in full. Source of the standard context events, `@EventListener` condition SpEL
  variables (`#root.event`, `#root.args`, `#argName`, `#a0`), returned-event republication,
  `ResolvableTypeProvider` for generic events, the async-listener limitations,
  `SimpleApplicationEventMulticaster` with `taskExecutor` and `errorHandler`, the "do not make
  listener beans lazy" warning, the three `MessageSource` implementations, and
  `ApplicationStartup`/`StartupStep`. Basis of §1.15 and §1.19.7–§1.19.9.
- <https://docs.spring.io/spring-framework/reference/core/aop/ataspectj/advice.html> — fetched in
  full. Source of the five advice annotations, the **intra-aspect precedence order**
  `@Around` → `@Before` → `@After` → `@AfterReturning` → `@AfterThrowing` (§1.13.4), the
  across-aspect `@Order` rule, the full `JoinPoint`/`ProceedingJoinPoint` API, the ten supported
  pointcut designators (§1.13.8), parameter binding and `argNames`, and the `-parameters`
  requirement. Basis of §1.13.
- <https://docs.spring.io/spring-framework/reference/core/aop-api.html> — fetched. Source of the
  low-level AOP surface: `Pointcut`/`ClassFilter`/`MethodMatcher.isRuntime()`, the advice
  interfaces, `Advisor`/`PointcutAdvisor`, `ProxyFactory`/`ProxyFactoryBean`/`AdvisedSupport`/
  `Advised`, the five auto-proxy creators, `TargetSource`, and
  `ReflectiveMethodInvocation`/`CglibMethodInvocation`. Basis of §1.13.14–§1.13.18.
- <https://docs.spring.io/spring-framework/reference/core/aop/proxying.html> — the proxy-selection
  rule (CGLIB when `optimize`, `proxyTargetClass`, or no interfaces). Basis of §1.12.5 and §3.7.8.
- <https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative.html> —
  fetched in full. Source of the `@Transactional` attribute list including `timeoutString` and
  `label` (§1.14.6), `TransactionInterceptor`/`TransactionAspectSupport`/
  `AnnotationTransactionAttributeSource`, the default rollback rule and its EJB-CMT origin,
  the `RollbackRuleAttribute` most-specific-wins rule, `AdviceMode.PROXY` vs `ASPECTJ`, and
  `@EnableTransactionManagement`'s three attributes. Basis of §1.14 and §3.8.
- <https://docs.spring.io/spring-framework/reference/core/validation/convert.html> — fetched.
  Source of `Converter`/`ConverterFactory`/`GenericConverter`/`ConditionalGenericConverter`, the
  `ConversionService` method set, `DefaultConversionService`, `ConversionServiceFactoryBean`, and
  the **`conversionService` bean-name** requirement (§1.18.4). Basis of §1.18.
- <https://docs.spring.io/spring-framework/reference/core/expressions.html> — fetched. Source of
  the SpEL feature inventory, `SpelExpressionParser`, `StandardEvaluationContext` vs
  `SimpleEvaluationContext`, `#root`/`#this`, `@bean`/`&factoryBean`, safe navigation, Elvis,
  selection `?[]`, projection `![]`, and the container integration points. Basis of §1.17.
- <https://docs.spring.io/spring-framework/reference/core/beans/factory-extension.html> — the
  `BeanPostProcessor` ordering rule (`PriorityOrdered` then `Ordered`; programmatically registered
  processors ignore ordering and run in registration order). Basis of §1.10.11. Consulted via
  search summary; **re-verify the exact wording in the write pass**.
- <https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-servlet.html> and
  <https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-servlet/special-bean-types.html>
  — fetched. Source of the special-bean-type list (`HandlerMapping`, `HandlerAdapter`,
  `HandlerExceptionResolver`, `ViewResolver`, `LocaleResolver`/`LocaleContextResolver`,
  `MultipartResolver`, `FlashMapManager`) and the root-vs-servlet context hierarchy. Basis of
  §1.23.1–§1.23.4. **`ThemeResolver`'s removal in 6.0 is from recall and is tagged
  `[VERSION-TRAP]` — verify.**
- <https://docs.spring.io/spring-framework/reference/integration/cache.html> — fetched. Source of
  the cache annotation attribute lists, `SimpleKeyGenerator`/`SimpleKey`, `@EnableCaching`
  attributes, `CacheInterceptor`, and the JSR-107 annotation set. Basis of §1.25.
- <https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html>
  — fetched in full. Source of the **ten** cache-key components (§3.12.2), the default max size
  **32**, the `spring.test.context.cache.maxSize` property, LRU eviction, the
  `org.springframework.test.context.cache` DEBUG logging category, the static-field caveat, and
  the `@DirtiesContext` listeners. Basis of §3.12.
- <https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/support/AbstractApplicationContext.html>
  and the 6.2.x source on GitHub (below) — `refresh()`'s twelve steps and the bean-name constants.

**Spring Framework source (primary)**

- <https://raw.githubusercontent.com/spring-projects/spring-framework/6.2.x/spring-context/src/main/java/org/springframework/context/support/AbstractApplicationContext.java>
  — fetched. Confirmed the twelve `refresh()` steps in order, `MESSAGE_SOURCE_BEAN_NAME =
  "messageSource"`, `APPLICATION_EVENT_MULTICASTER_BEAN_NAME = "applicationEventMulticaster"`,
  `LIFECYCLE_PROCESSOR_BEAN_NAME = "lifecycleProcessor"`, `CONVERSION_SERVICE_BEAN_NAME`, and the
  6.2 `startupShutdownLock` / `startupShutdownThread` / `earlyApplicationEvents` /
  `applicationStartup` fields. Basis of §3.1. **The write pass must quote the actual `refresh()`
  body from this file.**
- <https://raw.githubusercontent.com/spring-projects/spring-framework/6.2.x/spring-beans/src/main/java/org/springframework/beans/factory/support/DefaultSingletonBeanRegistry.java>
  — fetched. Confirmed the cache field types and capacities: `singletonObjects`
  `ConcurrentHashMap` **256**, `singletonFactories` **16**, `earlySingletonObjects` **16**,
  `registeredSingletons` synchronized `LinkedHashSet` **256**, `singletonsCurrentlyInCreation`
  and `inCreationCheckExclusions` `ConcurrentHashMap.newKeySet(16)`, `dependentBeanMap` and
  `dependenciesForBeanMap` **64**, `disposableBeans` `LinkedHashMap`. Also surfaced the **6.2
  lenient-creation** fields `lenientCreationLock`, `lenientCreationFinished`,
  `singletonsInLenientCreation`, `lenientWaitingThreads`, `currentCreationThreads` (§2.11.9,
  §3.4.14). Basis of §3.4. **The write pass must quote `getSingleton(String, boolean)` verbatim
  from this file.**
- <https://raw.githubusercontent.com/spring-projects/spring-framework/6.2.x/spring-beans/src/main/java/org/springframework/beans/factory/support/AbstractAutowireCapableBeanFactory.java>
  — fetched. Confirmed the `createBean` → `doCreateBean` → `initializeBean` call order, the
  `createBeanInstance` / `applyMergedBeanDefinitionPostProcessors` / `addSingletonFactory` +
  `getEarlyBeanReference` / `populateBean` / `initializeBean` /
  `registerDisposableBeanIfNecessary` sequence, `invokeAwareMethods` +
  `applyBeanPostProcessorsBeforeInitialization` + `invokeInitMethods` +
  `applyBeanPostProcessorsAfterInitialization` inside `initializeBean`, `allowCircularReferences`
  defaulting to **true** at the factory level, and the exact "injected into other beans […] in its
  raw version as part of a circular reference, but has eventually been wrapped" message
  (§3.3.13). Basis of §3.3.
- `DefaultAopProxyFactory`, `CglibAopProxy`, `JdkDynamicAopProxy`, `ReflectiveMethodInvocation`,
  `AbstractAutoProxyCreator`, `ConfigurationClassPostProcessor`, `ConfigurationClassEnhancer`,
  `ConfigurationClassParser`, `TransactionInterceptor`, `TransactionAspectSupport`,
  `AbstractPlatformTransactionManager`, `DataSourceTransactionManager`,
  `TransactionSynchronizationManager`, `AutoConfigurationImportSelector`,
  `AutoConfigurationSorter`, `ConditionEvaluationReport`, `SpringApplication`,
  `ConfigurationPropertyName`, `Binder` — **not fetched in this pass**; §3.5–§3.11 are written from
  the javadoc summaries plus recall and are tagged `[RESEARCH]` wholesale. The write pass must open
  each of these on the `6.2.x` / `3.5.x` branch and quote the relevant method before asserting any
  field name, callback index or constant. The highest-risk items are the **seven CGLIB callback
  indices** (§3.7.12), the `ReflectiveAspectJAdvisorFactory.METHOD_COMPARATOR` ordering (§3.7.6),
  the `AbstractFallbackTransactionAttributeSource` search order (§3.8.3), and the
  `AutoConfigurationSorter` three-stage sort (§3.10.15).

**Spring Boot reference documentation (primary)**

- <https://docs.spring.io/spring-boot/reference/features/external-config.html> — fetched in full.
  Source of the **fifteen-entry** property-precedence list (§1.22.1), the config-data file order,
  the five default locations, `spring.config.name`/`location`/`additional-location`/`import`/
  `on-not-found`, the `optional:` prefix, wildcard-location rules, `configtree:` and `env:`
  imports, extension and encoding hints, multi-document files and
  `spring.config.activate.on-profile`/`on-cloud-platform`, `SPRING_APPLICATION_JSON` and its
  null-handling, `RandomValuePropertySource`, the three binding modes plus records,
  `@ConstructorBinding`, `@DefaultValue`, `@Name`, `@EnableConfigurationProperties` /
  `@ConfigurationPropertiesScan`, the `<prefix>-<fqn>` bean name, the relaxed-binding and
  environment-variable rules, `Duration`/`Period`/`DataSize` conversion,
  `@ConfigurationPropertiesBinding`, `setEnvironmentPrefix`, and the `env`/`configprops`
  endpoints. Basis of §1.22 and much of §2.10.
- <https://docs.spring.io/spring-boot/reference/features/spring-application.html> — fetched in
  full. Source of the ordered Boot application-event list (§1.15.15), `spring.main.*` options,
  lazy initialization, banner variables, the `WebApplicationType` detection algorithm,
  `ApplicationArguments`, `ApplicationRunner` vs `CommandLineRunner`, `ExitCodeGenerator`,
  `spring.application.admin.enabled`, `ApplicationStartup`/`BufferingApplicationStartup(2048)`/
  `FlightRecorderApplicationStartup`, `spring.threads.virtual.enabled` and
  `spring.main.keep-alive`. Basis of §1.20 and §3.10.
- <https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html> —
  fetched in full. Source of the complete Boot condition inventory (§1.21.7), the
  `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` path and its
  `#`/`$` conventions, the `.replacements` file, `@AutoConfiguration(before/after/beforeName/
  afterName)`, `@AutoConfigureOrder`/`Before`/`After`, the "only use `@ConditionalOnBean` in
  auto-configuration" rule, the "declare a concrete return type" rule, the
  `ApplicationContextRunner` family with `withConfiguration`/`withPropertyValues`/
  `withUserConfiguration`/`FilteredClassLoader`, `ConditionEvaluationReportLoggingListener`, and
  `spring-boot-autoconfigure-processor`. Basis of §1.21.
- <https://docs.spring.io/spring-boot/reference/packaging/aot.html> and
  <https://docs.spring.io/spring-framework/reference/core/aot.html> — consulted via search summary.
  Source of `BeanRegistrationAotProcessor`, `RuntimeHints`, `@ImportRuntimeHints`,
  `@RegisterReflectionForBinding`, and the AOT limitation list (fixed classpath, beans cannot
  change at runtime, `@Profile` and `@ConditionalOnProperty` constraints, and the warning that a
  `BeanRegistrationAotProcessor` bean plus all its dependencies are initialised during AOT
  processing). Basis of §3.11. **Not fetched in full — re-fetch both pages in the write pass.**
- <https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.5-Release-Notes> — fetched in
  full. Source of every Boot 3.5 delta used here: strict `.enabled` boolean parsing, profile-name
  validation and `spring.profiles.validate`, the removal of the `taskExecutor` alias in favour of
  `applicationTaskExecutor` (`TaskExecutionAutoConfiguration.APPLICATION_TASK_EXECUTOR_BEAN_NAME`),
  the auto-configured `bootstrapExecutor`, `spring.task.execution.mode=force`, the heapdump
  endpoint defaulting to `access=NONE`, repeatable `@ConditionalOnProperty`/
  `@ConditionalOnBooleanProperty`, generic-aware `@ConditionalOnBean`/`@ConditionalOnMissingBean`,
  and lambda `@ConfigurationPropertiesBinding` beans. Basis of §2.14.19 and the scattered Boot 3.5
  leaves.
- <https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide> — the
  `jakarta.*` migration, `spring.factories` auto-config removal, and `@ConstructorBinding`
  relocation. Basis of §2.14.15. Consulted via search result listing only; **re-fetch.**

**Version-delta sources**

- <https://spring.io/blog/2024/04/11/spring-framework-6-2-0-m1-all-the-little-things/> — fetched.
  Confirmed `@Fallback`, `@Bean(bootstrap = BACKGROUND)`, the placeholder-parser rewrite with a
  configurable **backslash** escape character and lazy default-value resolution, and
  `TaskDecorator` support for scheduled tasks. It did **not** confirm the lenient-locking rework,
  `BeanRegistrar`, or the null-safety work — those came from the source file and the 7.0 GA post
  respectively, and both stay `[RESEARCH]`.
- <https://spring.io/blog/2025/11/13/spring-framework-7-0-general-availability/> and
  <https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes> — consulted
  via search summary for the 7.0/4.0 delta list (JSpecify, API versioning, `BeanRegistrar`, core
  resilience with `@Retryable`/`@ConcurrencyLimit`, `JmsClient`, `RestTestClient`, Jackson 3,
  modularised autoconfigure jars, Jakarta EE 11, Java 25 target with a Java 17 baseline). Basis of
  §2.14.9 and §2.14.20. **Neither page was fetched directly; every 7.0/4.0 claim is
  `[VERSION-TRAP]` + `[RESEARCH]` and must be verified before the write pass states it.**
- <https://www.baeldung.com/spring-bean-background-init> and
  <https://2024.springio.net/slides/spring-framework-62-core-container-revisited-springio24.pdf>
  (Jürgen Hoeller, "Spring Framework 6.2 Core Container Revisited") — background bean
  initialisation semantics and the bootstrap-executor model. Basis of §1.9.18. The PDF was
  **not** fetched; it is the single best primary source for §2.11.9 and §3.4.14 and should be read
  in the write pass.
- <https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html> — graceful shutdown as
  the earliest `SmartLifecycle` stop phase and
  `spring.lifecycle.timeout-per-shutdown-phase=20s`-style configuration. Basis of §1.9.13 and
  §2.11.5. Consulted via search summary.

**Interview / curriculum / adversarial angles**

- <https://www.vmexam.com/vmware/vmware-spring-professional-develop-certification-exam-syllabus>
  and <https://www.spring-certification.com/spring-exam-details> — the Spring Certified
  Professional (2V0-72.22) objective weights: Container/DI/IoC **20%**, Spring Boot **28%**,
  Data/JDBC/Transactions **14%**, Testing **14%**, MVC/Web **10%**, AOP **8%**, Security **6%**.
  Used as a completeness checklist against PART 1 and PART 2; it is why §1.18 (validation),
  §1.19 (resources/`MessageSource`) and §2.12 (testing the container) exist as first-class
  sections rather than footnotes. `[RESEARCH]`
- Senior-level Spring Boot interview question compilations (Medium/InterviewBit/roadmap.sh
  listings surfaced in search) — mined only for **question names** not already in §5.1. They
  contributed the "which other annotations share `@Transactional`'s proxy limitation",
  "`BeanPostProcessor` vs `BeanFactoryPostProcessor`", and "`@Transactional` on a `@Bean` method
  called from the same `@Configuration` class" framings. No prose or numbers were taken from them.
- `@Transactional` pitfall write-ups (javacodegeeks, dev.to, stackademic, thecodeforge) — mined for
  the *failure taxonomy* only: self-invocation, private/final methods, checked-exception commit,
  `REQUIRES_NEW` deadlock against the suspended outer transaction, the global `readOnly = true`
  trap, exception swallowing, and long-running transactions. Every one of those became a §5.2 leaf.
  No constant was taken from a blog.

**Searches that returned nothing usable**

- No published *university course* syllabus on the Spring container was found; the curriculum angle
  was covered by the certification objectives instead.
- No primary source was found giving the current `ConfigurationClassEnhancer` callback array or the
  `CglibAopProxy` callback indices; §3.5.9 and §3.7.12 therefore instruct the write pass to read
  them from the 6.2.x source rather than quoting a remembered layout.
- No authoritative benchmark for Spring proxy per-call overhead was located; §1.12.16 must be
  written as "measure it with JMH" (`06-jvm-internals.md`) rather than quoting a number.

## Gaps vs the current guide

`src/topics/07-spring-core.md` is **456 lines** across 14 sections plus a 26-item checklist. It is
an unusually good short guide — its proxy, self-invocation and `@Transactional` sections are
already mechanism-first, and every one of its `**Trap:**` markers is real and must survive. It is
still not a bible: it has no `refresh()` walk, no `BeanDefinition` model, no extension-point SPI,
no AOP API surface, no `Environment`/SpEL/conversion layer, no AOT, no testing-container content,
no version history, no build-it content, and no interview set.

| Syllabus area | Present in `src/topics/07-spring-core.md` | Missing | Shallow |
|---|---|---|---|
| §1.1 why IoC exists, DI vs service locator, module map, Jakarta migration | §1 (2 sentences on "why IoC at all") | ✅ origin story, IoC-vs-DI, module list, `jakarta.*`, baselines, JSR-330 | ✅ |
| §1.2 container types, `BeanFactory` vs `ApplicationContext`, context implementations | §1 (one clause) | ✅ the whole interface hierarchy, parent contexts, refreshable vs generic, `WebApplicationType` | ✅ |
| §1.3 `BeanDefinition` model | §1 ("a map of name → metadata") | ✅ the property surface, `ROLE_*`, merged definitions, naming rules, overriding, `@DependsOn`, `@Lazy` | ✅ severely |
| §1.4 where definitions come from, `@Import`, `FactoryBean` | — | ✅ entire section | |
| §1.5 stereotypes and meta-annotations | §3 (table + `@Repository` mechanics) | ✅ `@AliasFor`, `MergedAnnotations`, composed annotations, retention rule, the full `DataAccessException` list | ✅ the table and the `@Service` trap are strong and must be preserved verbatim |
| §1.6 DI styles | §2 (four arguments, field-injection mechanism) | ✅ constructor-selection algorithm, `required` semantics, `@Resource`/`@Inject`, `ObjectProvider` surface, `@Lookup`, resolvable dependencies, self-injection, the BPP restriction | ✅ the four arguments are excellent and must be preserved verbatim and expanded |
| §1.7 candidate resolution | §2 (four-step resolution order) | ✅ `@Fallback`, `@Priority`, generic matching, `autowireCandidate`, `Ordered` constants, `-parameters` | ✅ |
| §1.8 scopes | §4 (singleton trap + prototype capture) | ✅ all six scopes, `Scope` SPI, custom scopes, `RequestContextHolder`, destruction table, `websocket`, virtual-thread interaction | ✅ the stateful-singleton code example and the prototype fixes must be preserved verbatim |
| §1.9 lifecycle | §6 (the ordered list) | ✅ the `Aware` inventory, inferred `destroyMethod`, `SmartLifecycle`/phases, graceful shutdown, `close()`, background bootstrap | ✅ the order list and both `@PostConstruct` traps must be preserved verbatim |
| §1.10 extension points | §1 (BFPP mentioned once) | ✅ the whole SPI, the built-in processor inventory, ordering, the not-eligible-for-post-processing trap, initializers, `EnvironmentPostProcessor`, `FailureAnalyzer` | ✅ severely |
| §1.11 `@Configuration` full vs lite | §5 (one paragraph) | ✅ `@Bean` attributes, static `@Bean`, CGLIB constraints, `@ImportAware`, `@Conditional`, overloaded-method `@Profile` | ✅ |
| §1.12 the proxy model | §5 (table + CGLIB mechanics + traps) | ✅ Objenesis, `AopUtils`, `$$SpringCGLIB$$` naming, Kotlin `allopen`, records, AspectJ weaving, cost | ✅ the JDK-vs-CGLIB table, the CGLIB mechanics paragraph and the `@Transactional private` trap must be preserved verbatim |
| §1.13 AOP vocabulary and API | — | ✅ entire section — the guide never mentions `@Around`, pointcuts, advisors or ordering at all | |
| §1.14 `@Transactional` model | §7 (mechanism, propagation table, rollback rules, `readOnly`) | ✅ the attribute list, manager implementations, `TransactionSynchronization`, `NESTED` details, `setRollbackOnly`, `TransactionTemplate`, `TransactionSystemException` | ✅ the propagation table, the rollback-rule trap, the `UnexpectedRollbackException` explanation and the `readOnly` paragraph are the guide's best content and must be preserved verbatim and expanded |
| §1.15 events | §11 (three listener types + four bullets) | ✅ `PayloadApplicationEvent`, conditions, generics, multicaster, context events, the Boot event sequence, early-event registration | ✅ all four bullets are correct and must be preserved |
| §1.16 environment and profiles | §9 (precedence + profiles trap) | ✅ the `Environment` API, `MutablePropertySources`, `@PropertySource`, placeholder mechanics, Boot 3.5 profile validation | ✅ the abbreviated precedence list must be replaced with the full fifteen and the profiles/secrets trap preserved |
| §1.17 `@Value` and SpEL | §9 (one line on `@Value`) | ✅ entire section including the SpEL security boundary | ✅ severely |
| §1.18 conversion, formatting, validation | §10 (validation, 4 lines) | ✅ the whole conversion SPI, Boot's converters, `@Validated` making a bean proxied, 6.1 method validation | ✅ the two-exception trap must be preserved |
| §1.19 resources and `MessageSource` | — | ✅ entire section including the fat-jar `getFile()` trap | |
| §1.20 what Boot is, starters, fat jar | §8 (starter definition, 3 lines) | ✅ `@SpringBootApplication` decomposition, the BOM, fat-jar layout, layers, plugin goals, actuator surface | ✅ the "a starter is a dependency aggregator" paragraph must be preserved |
| §1.21 auto-configuration | §8 (import selector, condition table, `--debug`) | ✅ `@AutoConfiguration`, ordering, the full condition inventory, `matchIfMissing`, the return-type trap, `.replacements`, metadata filtering, `ApplicationContextRunner` | ✅ the condition table and the conditions-report advice must be preserved verbatim |
| §1.22 externalized config | §9 (`@ConfigurationProperties` + abbreviated precedence) | ✅ the full precedence list, config-data locations, `spring.config.import`, multi-document, relaxed-binding rules, records, validation, metadata, `Binder` | ✅ the "prefer `@ConfigurationProperties`" argument must be preserved and expanded into a table |
| §1.23 MVC flow | §10 + §12 (flow diagram, advice, validation, filter table) | ✅ special bean types, argument resolvers, message converters, exception-resolver chain, `OncePerRequestFilter`, async MVC, embedded-server config, `@EnableWebMvc` trap | ✅ the flow diagram, the entity-return trap and the filter/interceptor/aspect table are strong and must be preserved verbatim |
| §1.24 scheduling and `@Async` | §13 (two traps) + §11 (`@Async` bullet) | ✅ the attribute surface, six-field cron, executor properties and defaults, `TaskDecorator`, Boot 3.5 changes, Quartz | ✅ both `@Scheduled` traps and the `fixedDelay`/`fixedRate` distinction must be preserved verbatim |
| §1.25 caching abstraction | §5 (mentioned as a proxy example) | ✅ entire section | |
| PART 2 — the master tables | — | ✅ all nine | |
| PART 2 — wiring decisions | §2 (constructor injection argument) | ✅ the rest | ✅ |
| PART 2 — lifetime mismatch | §4 | ✅ custom scopes, the `@Async` access failure, prototype resource leaks | ✅ |
| PART 2 — what can be advised (checklist) | §5 (partial) | ✅ the five-question checklist, runtime verification, advisor ordering | ✅ |
| PART 2 — self-invocation fixes | §5 (ranked fixes, review advice) | ✅ the `@Lazy` proof, `ObjectProvider`, ArchUnit enforcement, lite-mode variant | ✅ the ranked fix list and the review heuristic must be preserved verbatim |
| PART 2 — propagation in practice, pool arithmetic | §7 (partial) | ✅ the audit-row comparison, the pool-exhaustion arithmetic, the nesting matrix, multiple managers | ✅ |
| PART 2 — rollback rules in practice | §7 | ✅ the composed annotation, catch-and-continue, commit-time exceptions, `@Retryable` interaction | ✅ |
| PART 2 — events in practice | §11 | ✅ the decision table, idempotency, testing, Modulith | ✅ |
| PART 2 — auto-configuration in practice | §8 | ✅ the diagnosis procedure, the `*Customizer` idiom, writing a company starter | ✅ |
| PART 2 — configuration in practice | §9 | ✅ layering, secrets, fail-fast, `/actuator/env` debugging, migration recipe | ✅ |
| PART 2 — startup/shutdown/concurrency | — | ✅ entire section including graceful shutdown and container thread-safety | |
| PART 2 — testing the container | — | ✅ entire section — and the context-cache-key point is the highest-value thing missing | |
| PART 2 — observing the container | §8 (`--debug` only) | ✅ the actuator endpoints, the three log categories, reading a transaction TRACE log, proxy inspection | ✅ |
| PART 2 — version delta 4 → 7 / Boot 1 → 4 | §8 + §14 (two version notes) | ✅ the whole timeline and the stale-answer sweep list | ✅ |
| PART 2 — anti-pattern catalogue | scattered traps | ✅ consolidated, plus the static-field-injection and `@EnableWebMvc` entries | ✅ |
| PART 3 — `refresh()`'s twelve steps | — | ✅ | |
| PART 3 — `DefaultListableBeanFactory` internals | — | ✅ | |
| PART 3 — `createBean`/`doCreateBean`/`initializeBean` | — | ✅ | |
| PART 3 — the three-level cache | §14 (one sentence: "three-level singleton cache") | ✅ the field declarations, the two `getSingleton` methods, the why-three proof, `getEarlyBeanReference`, the `@Async` cycle failure, lenient creation | ✅ severely — this is the most-asked internals question and the guide gives it one clause |
| PART 3 — `ConfigurationClassPostProcessor` and the enhancer | §5 (one paragraph on `@Configuration` proxying) | ✅ the parser order, deferred selectors, `BeanMethodInterceptor`, the `FactoryBean` case, scanning internals | ✅ |
| PART 3 — annotation-injection internals | §2 (one sentence on `setAccessible`) | ✅ `InjectionMetadata`, constructor-candidate caching, `EventListenerMethodProcessor` | ✅ |
| PART 3 — AOP proxy creation internals | — | ✅ entire section — `wrapIfNecessary`, `ReflectiveMethodInvocation.proceed()`, the CGLIB callbacks, Objenesis, the advisor chain cache | |
| PART 3 — `TransactionInterceptor` internals | §7 (the mechanism in three sentences) | ✅ `invokeWithinTransaction`, the attribute search order, `rollbackOn`, `handleExistingTransaction`, suspend/resume, `processCommit`, `globalRollbackOnParticipationFailure`, the AspectJ mode | ✅ |
| PART 3 — scope/event/SpEL internals | — | ✅ | |
| PART 3 — `SpringApplication.run()` internals | §8 (the import selector only) | ✅ the whole run sequence, `ConfigDataEnvironment`, `prepareContext`, `AutoConfigurationSorter`, `ConditionEvaluationReport`, `ConfigurationPropertyName` | ✅ |
| PART 3 — AOT and native | — | ✅ entire section | |
| PART 3 — TestContext internals and the cache key | — | ✅ entire section | |
| PART 3 — the Boot loader and packaging | — | ✅ entire section | |
| PART 3 — failure modes read at source level | scattered | ✅ the decision tree, the trace anatomies, the silent-failure catalogue | ✅ |
| PART 4 — every `[BUILD]` (§4.1–§4.10) | — | ✅ all 62 leaves; the current guide contains no implementable content whatsoever | |
| PART 5 — the 110-question set | — | ✅ | |
| PART 5 — the 84-item trap index | 11 `**Trap:**` markers inline | ✅ all eleven must be preserved and 73 added | |
| PART 5 — numbers/class-name/ordering/diagnosis/version/whiteboard/review drills | closing checklist (26 lines) | ✅ the drills | ✅ the checklist must be preserved verbatim and extended |

Three corrections the write pass **must** make to existing text, not merely additions:

1. §9 of the current guide gives an *abbreviated* property-precedence list of six entries and calls
   it "abbreviated". The real list is fifteen entries and the abbreviation drops
   `SPRING_APPLICATION_JSON`, `RandomValuePropertySource`, and every test-only source — which is
   exactly the group that surprises people when a `@TestPropertySource` value refuses to be
   overridden. State all fifteen.
2. §11 says the default `@Async` executor in Boot 3 "is a virtual-thread or
   `SimpleAsyncTaskExecutor`-based one". In Boot 3.5 the auto-configured bean is
   `applicationTaskExecutor` — a `ThreadPoolTaskExecutor` by default, and a virtual-thread
   `SimpleAsyncTaskExecutor` only when `spring.threads.virtual.enabled=true`. Boot 3.5 also
   **removed** the `taskExecutor` alias. The current wording implies virtual threads are the
   default, which they are not.
3. §14 says circular references "can be resolved via the three-level singleton cache (an early
   reference is exposed before initialization completes)" and stops. That is true but omits the
   two things the reader needs: **why three levels rather than two** (the AOP early-reference
   factory), and the case where the cache does **not** save you (`@Async`, §3.4.8). Both must be
   proved, not asserted.

Eight passages in the current guide are strong and must survive **verbatim or expanded**, never
rewritten: the four arguments for constructor injection (§2), the stereotype table plus the
`@Service`-does-nothing trap (§3), the stateful-singleton code example (§4), the
JDK-vs-CGLIB table and CGLIB-mechanics paragraph (§5), the ranked self-invocation fixes (§5), the
lifecycle order list with its two proxy consequences (§6), the propagation table plus the
`UnexpectedRollbackException` explanation and the `readOnly` paragraph (§7), and the
filter/interceptor/aspect table (§12).

---

## Footer — leaf counts

| Part | Sections | Leaves |
|---|---|---|
| PART 1 — Basics | §1.1–§1.25 | 397 |
| PART 2 — Intermediate | §2.1–§2.15 | 146 |
| PART 3 — Under the hood | §3.1–§3.14 | 210 |
| PART 4 — Build it | §4.1–§4.10 | 62 |
| PART 5 — Interview and retention | §5.1–§5.3 | 207 |
| **Total** | **67 sections** | **1022 leaves** |

`[RESEARCH]`-tagged leaves: **118** (PART 1: 52, PART 2: 24, PART 3: 38, PART 4: 0, PART 5: 4).
Each must be re-verified against its cited source during the write pass before any constant from it
is written down. The highest-risk clusters are: everything in §3.5–§3.11 that names a field,
callback index or comparator in Spring source that was **not** fetched in this pass (the
`ConfigurationClassEnhancer` callbacks, the seven `CglibAopProxy` callbacks, the
`ReflectiveAspectJAdvisorFactory.METHOD_COMPARATOR`, the
`AbstractFallbackTransactionAttributeSource` search order, the `AutoConfigurationSorter` stages);
every Spring Framework 7.0 / Spring Boot 4.0 claim in §2.14.9 and §2.14.20 (both release pages were
read only via search summary); the Boot server and executor defaults in §1.23.18 and §1.24.9
(verify with `/actuator/configprops` on a real 3.5 app, not from recall); the 6.2 lenient-creation
mechanics in §2.11.9 and §3.4.14; and the `SpelCompilerMode` threshold in §3.9.10, which is
deliberately left unstated here.

Target version restated for the write pass: **Spring Framework 6.2.x / Spring Boot 3.5.x on
Java 21**, with every Framework 7.0 / Boot 4.0 divergence marked `[VERSION-TRAP]` inline. The
version deltas that most often produce a stale answer are `spring.factories` for
auto-configuration (removed in Boot 3.0), the JDK-proxy default (gone since Boot 2.0), circular
references (disabled since Boot 2.6), `@ConstructorBinding` placement (moved in Boot 3.0),
`javax.*` (gone in Framework 6.0), and `@MockBean`/`@SpyBean` (superseded by `@MockitoBean`/
`@MockitoSpyBean` in Framework 6.2).
