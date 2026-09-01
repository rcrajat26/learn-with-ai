# 04 — Spring Framework

**What this decides:** whether Spring *foundations* (proxy model, bean
lifecycle, auto-configuration) must be added as prerequisite sessions before
the prep plan's sharp-edges track (N+1, propagation, pool tuning), or whether
you can enter that track directly.

---

## Ladder

### Q1 [L1] explain-back — What problem does dependency injection solve?
**Strong answer:** decouples construction from use; dependencies are provided,
not `new`-ed → swappable implementations, testability (inject mocks),
centralized wiring. IoC = the container calls you.
**Red flags:** "it's how Spring creates beans" with no *why*.

### Q2 [L1] explain-back — `@Component` vs `@Bean` vs `@Service`
When do you use each?
**Strong answer:** `@Component` (and stereotypes `@Service`/`@Repository`/
`@Controller` — same mechanics, semantic labels + some extras like exception
translation on `@Repository`) marks a class for component scanning; `@Bean`
is a method-level factory inside `@Configuration` — used for third-party
classes you can't annotate or when construction needs logic.

### Q3 [L2] explain-back + trap — Bean scopes
What's the default scope? A singleton `@Service` has a field
`private List<String> recentItems = new ArrayList<>()` that a request handler
adds to. What's wrong?
**Strong answer:** singleton default → ONE instance shared across all
requests/threads: cross-request data bleed + race conditions. Fixes:
stateless services (move state to method scope / DB / cache), or
request/prototype scope if truly needed. Must connect singleton → shared →
concurrent mutation.

### Q4 [L2] explain-back — The proxy model (the key question in this file)
How do `@Transactional`, `@Cacheable`, `@Async` actually work at runtime?
**Strong answer:** Spring wraps the bean in a proxy (JDK dynamic proxy for
interfaces / CGLIB subclass otherwise); callers hold the proxy; the proxy
runs the interceptor logic (open txn, check cache) around the real call.
Consequences: only *external* calls pass through the proxy; `final`/private
methods can't be proxied by CGLIB.
**Red flags:** "Spring uses AOP" without being able to say what the proxy
does → 0.5. **L0–L1 here mandates the foundations prerequisite in gaps.md.**

### Q5 [L2] explain-back — Bean lifecycle hooks
Name the ways to run code after a bean's dependencies are injected, and one
reason constructor logic is sometimes too early.
**Strong answer:** `@PostConstruct`, `InitializingBean`, `initMethod`;
constructor runs before field/setter injection completes (for field
injection) and before proxying/post-processors. Bonus: `BeanPostProcessor`
awareness, `@PreDestroy`.

### Q6 [L3] predict-output — Self-invocation
```java
@Service
public class OrderService {
    @Transactional
    public void process(Order o) { save(o); this.audit(o); }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void audit(Order o) { auditRepo.save(auditOf(o)); }
}
```
`process()` is called from a controller. Does `audit` run in a new
transaction? Why? Two fixes?
**Strong answer:** No — `this.audit(o)` bypasses the proxy, so
`REQUIRES_NEW` is silently ignored; audit joins the outer transaction.
Fixes: move `audit` to another bean; self-inject the proxy
(`@Lazy @Autowired OrderService self`); (mention-only) AspectJ weaving.
Full credit requires the proxy-bypass mechanism, not just "it doesn't work."

### Q7 [L3] spot-the-bug — Injection style
```java
@Service
public class ReportService {
    @Autowired private UserClient userClient;
    @Autowired private ReportRepo repo;
}
```
A teammate asks you to review. What do you say, and what breaks first?
**Strong answer:** field injection → can't construct without reflection
(tests need `@InjectMocks`/Spring context), hides growing dependency count,
allows circular deps to slip through, no immutability. Prefer constructor
injection (single constructor auto-wires, fields `final`). Breaks first: unit
tests. Bonus: circular dependency with constructor injection fails fast at
startup — and that's a *feature*.

### Q8 [L3] predict-output — Exception rollback
```java
@Transactional
public void importFile(File f) throws IOException {
    repo.save(parseHeader(f));          // succeeds
    parseBody(f);                        // throws IOException
}
```
Does the header row roll back?
**Strong answer:** No — default rollback is on unchecked exceptions/Error
only; `IOException` is checked → commit happens. Fix:
`@Transactional(rollbackFor = Exception.class)` or wrap in unchecked.
Knowing the checked/unchecked default is the point.

### Q9 [L4] discriminator — Filter vs interceptor vs aspect
You need to (a) reject requests missing an API key, (b) log execution time
of every service-layer method, (c) add a header to every response. Which
mechanism for each and why?
**L2 answer:** defines each. **L3:** (a) servlet `Filter`/Security filter
chain — before DispatcherServlet, can short-circuit; (b) AOP aspect — service
layer isn't web-scoped; (c) filter or `ResponseBodyAdvice`. **L4:** ordering
concerns (filter chain order, aspect precedence), what each can/can't see
(filter: raw request; interceptor: handler info; aspect: method args), and
proxy limitations tying back to Q4. Score by tier matched (L2 = 0.5).

### Q10 [L4] discriminator — Auto-configuration
"Your app has an embedded Tomcat, a Jackson ObjectMapper, and a DataSource
you never defined. How did they get there, and how would you find out why a
specific bean exists or was backed off?"
**Strong answer:** starters put auto-configuration classes on the classpath;
`@EnableAutoConfiguration` imports them; `@ConditionalOnClass` /
`@ConditionalOnMissingBean` decide activation — your own bean wins via
back-off. Debug: `--debug` conditions evaluation report, actuator
`/conditions`. Bonus: `spring.factories` → `AutoConfiguration.imports`
(Boot 2.7+/3.x). L1 ("Spring Boot magic") = 0.

---

## Breadth checklist (rate 0–3)

- [CORE] Constructor injection as default style — and why
- [CORE] `@ControllerAdvice` / `@ExceptionHandler` — global error handling
- [CORE] Profiles (`@Profile`, `application-{profile}.yml`)
- [CORE] `@ConfigurationProperties` vs `@Value`
- [CORE] Bean validation (`@Valid`, `@NotNull`, custom validators)
- [CORE] `@Transactional` propagation names — can you list 3+ and their meaning?
- DispatcherServlet request flow (filter → dispatcher → handler mapping → controller → view/message converter)
- `RestTemplate` vs `WebClient` vs `RestClient` — status of each
- Spring events (`ApplicationEventPublisher`, `@EventListener`, `@TransactionalEventListener`)
- Actuator — endpoints you've actually used
- `@Scheduled` / `@EnableScheduling` — and its single-thread default trap
- Spring Security — filter chain concept (heard of? configured?)
- Caching abstraction (`@Cacheable` keys, eviction)
- Testing annotations: `@SpringBootTest` vs `@WebMvcTest` vs `@DataJpaTest`
- Circular dependencies — have you hit one? how resolved?
- BeanPostProcessor / BeanFactoryPostProcessor (0–1 is fine)
- Spring AOP vs AspectJ difference (0–1 is fine)
