# 04 Modern Java — `Optional` — INTERMEDIATE (§2.6)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [`Optional` — basics](01-basics.md) · Next: [`Optional` — internals optional](03-internals-optional.md)

This file is the discipline layer: not what `Optional` is, but the rules that keep a codebase
honest once fifty engineers are calling it. Every rule below exists because someone violated it
in production and the violation was expensive enough to write down. The QuizStakes examples run
through client lookups, wallet balances, and bonus eligibility — the places where "was there a
value or wasn't there" decides whether money moves.

---

### The rule set in one place

**Mental model first.** `Optional` is not a container you pass around — it is a **return-type
annotation with teeth**. The moment you write `Optional<Client>` as a method's return type, you
are telling every caller, in a form the compiler half-enforces and the JIT can optimise away,
"this method might not have an answer, and I refuse to let you find that out by calling `.get()`
on a `null`." Everywhere else in the language — a field, a parameter, a collection element, a map
value — `Optional` is not a stronger `null`, it is a second, incompatible way of expressing the
same absence, and having two costs you every time someone has to remember which one a given slot
uses.

**Why it exists.** Before Java 8, "might be absent" had no type-level signal at all. A method
returning `Client` might return `null`, might throw, might return a sentinel `Client.NONE` —
and the only way to find out was to read the implementation or get burned by a
`NullPointerException` in production. Brian Goetz's stated design intent (repeated on the
`amber-dev` and `core-libs-dev` mailing lists across 2014) was narrow: `Optional` exists **so
that a method's return type can carry the "maybe absent" contract that `null` cannot express**,
for library authors who want to make that contract explicit at API boundaries. It was never
designed as a general-purpose "maybe" monad for internal plumbing, and the rest of this file's
rules follow directly from that narrow intent.

**When to reach for it, and when not.** Reach for `Optional<T>` as a return type when the absence
is a normal, expected outcome the caller must handle — `ClientRepository.findById` might
legitimately find no client for a stale `ClientId`. Do **not** reach for it:

- **as a field** — a `Client` entity with `Optional<Money> pendingBonus` costs one extra object
  per instance, is not `Serializable` before you write a custom converter, and JPA/Hibernate does
  not map it directly (Hibernate 6 added *some* `Optional` property support, but the mapping is
  still narrower than a plain nullable column and most shops disable it). A plain nullable
  `Money pendingBonus` plus a `@Nullable` annotation says the same thing with zero extra
  allocation.
- **as a parameter** — see the anti-pattern below; the caller already had a value or didn't, and
  wrapping it in `Optional` only moves the `null`-check from one place to two.
- **as a collection element or map value** — `List<Optional<Restriction>>` and
  `Map<ClientId, Optional<Money>>` both have a strictly better representation: omit the entry.
  A `Map` already has a first-class "not present" signal — the key is missing — so wrapping the
  value in `Optional` on top of that is expressing the same fact twice, and now two different
  parts of the type carry it.
- **never null** — an `Optional` reference that is itself `null` is the worst possible outcome,
  because it defeats the entire mechanism: every caller now has to null-check the `Optional`
  *and* handle its emptiness, i.e. two absence channels instead of one. A method that returns
  `Optional<T>` must never `return null;` — return `Optional.empty()`.

**How it works.** The rule set is not JLS-enforced; nothing stops you compiling
`Optional<Client> field` as a field. The enforcement is entirely social and tooling-based:
code review, a static-analysis rule (Error Prone's `FieldCanBeStatic` sibling checks such as
`OptionalUsedAsFieldOrParameterType`, or a custom ArchUnit rule), and the fact that a `Optional`
field silently degrades the JIT's ability to scalar-replace the object (see leaf 2.6.12 below —
escape analysis cannot eliminate an allocation that outlives the frame that created it). The rule
about collections is stronger, because `Optional.empty()` inside a `List` still occupies a slot —
you pay for the wrapper *and* still have to check it, which is strictly worse than either a
`null` element (bad, but at least single-cost) or simply omitting the element (best).

**Example.** A client-facing profile endpoint deciding whether to show a pending bonus:

```java
public record ClientProfileView(ClientId clientId, Money stakeable, Money withdrawable,
                                 Money pendingBonus) {
    // pendingBonus is Money.ZERO when there is no pending bonus — not Optional<Money>,
    // and not null. The DTO has exactly one absence channel.
}

public final class ProfileService {

    private final BonusService bonusService;

    public ProfileService(BonusService bonusService) {
        this.bonusService = bonusService;
    }

    public ClientProfileView buildProfile(ClientId clientId, Money stakeable, Money withdrawable) {
        Money pendingBonus = bonusService.findActiveBonus(clientId)
                .map(Bonus::remainingAmount)
                .orElse(Money.ZERO);
        return new ClientProfileView(clientId, stakeable, withdrawable, pendingBonus);
    }
}
```

`BonusService.findActiveBonus` returns `Optional<Bonus>` — the return-type boundary, exactly
where the rule set says `Optional` belongs. The moment that `Bonus` is unwrapped into a plain
`Money` for the DTO, it leaves `Optional` behind; `ClientProfileView` never carries one.

**The gotcha.** The rule set is easy to state and easy to violate by omission: a Spring `@Entity`
with `private Optional<String> nationalInsuranceNumber` compiles, Hibernate 5 silently maps it as
if it were the raw type (throwing at runtime on some dialects, doing the wrong thing silently on
others), and the bug surfaces three sprints later as a `PropertyAccessException` nobody connects
to the field declaration. Grep for `Optional<` in `@Entity` classes as a standing code-review
habit — nothing else catches it reliably before runtime.

**Insight:** the four "never" rules are one rule, not four — `Optional` may only occupy the
single position in a method's signature where the type system can express "this value might be
absent" *at the call site*, i.e. the return type. Every other position already has its own way of
expressing absence (a `null` field with `@Nullable`, an overloaded method, an absent map entry),
and stacking `Optional` on top of one of those doubles the absence-signalling mechanisms instead
of replacing one.

> **`Optional` is a return-type-only signal that a method may have no answer — never a field,
> parameter, collection element, or map value, and never itself `null`.**

#### The chain style: never `isPresent()` + `get()`

This is the corollary that makes the rule set enforceable in practice, and it is a supporting
fact rather than a concept with its own tradeoff: once you accept that `Optional` is a
return-type signal, the only correct way to consume it is through the functional chain —
`map`/`flatMap`/`filter`/`or`/`orElseGet` — never the imperative pair
`if (opt.isPresent()) { opt.get() }`.

- **Mechanism.** `isPresent()` followed by `get()` is exactly the `null`-check-then-dereference
  pattern `Optional` was invented to retire, just spelled differently — it still requires the
  reader to trust that nothing runs between the check and the use, and it still crashes with
  `NoSuchElementException` (the `Optional` analogue of `NullPointerException`) if that trust is
  ever violated by a refactor that inserts a line between the two calls.
- **Gotcha:** `isPresent()` + `get()` also throws away the one thing the chain style buys you —
  a compile-time obligation to say what happens on absence. `opt.get()` alone compiles with no
  absence handling in sight; `opt.orElseThrow(() -> new RestrictedActionException(...))` puts the
  absence handling in the same expression as the success path, which is exactly the "chain style"
  leaf 2.6.2 in the syllabus names.

  ```java
  // Wrong — the check and the use can drift apart under a refactor
  Optional<Client> maybeClient = clientRepository.findById(clientId);
  if (maybeClient.isPresent()) {
      Client client = maybeClient.get();
      auditLog.record(client.id());
  }

  // Right — one expression, absence handled at the same point as presence
  clientRepository.findById(clientId)
          .map(Client::id)
          .ifPresent(auditLog::record);
  ```

> **`isPresent()` + `get()` is `null`-check-and-dereference wearing a disguise; the chain
> (`map`/`flatMap`/`filter`/`or`/`orElseGet`) is the only form that keeps the absence-handling
> obligation next to the success path.**

---

### `orElse` vs `orElseGet` vs `orElseThrow`: the decision table

**Mental model first.** These three methods answer the same question — "what happens when the
`Optional` is empty?" — but they answer it at three different *times*: `orElse` answers it
**before** the `Optional` is even asked whether it has a value, `orElseGet` answers it **only if**
asked, and `orElseThrow` answers it by refusing to answer at all. The whole decision table
collapses to one question: **is your fallback free, expensive, or an error?**

**Why it exists.** Java 8's designers needed three shapes because the three costs are
incompatible: a constant fallback (`Money.ZERO`) has no reason to defer, an expensive fallback
(a database round-trip) has every reason to defer, and "there is no fallback" is not a value at
all — it is a different control-flow exit. Collapsing these into a single overloaded method would
force every call site to either eagerly evaluate expensive fallbacks or wrap cheap ones in
needless lambdas.

**When to reach for it, and when not.** `orElse` for a genuinely free, already-computed constant.
`orElseGet` for anything that does work to produce — a query, a computation, a new object
allocation beyond the constant case. `orElseThrow` when absence is not a valid outcome for this
call site and the caller has no sensible default. Reaching for `orElse` with a
method-call argument is the single most common `Optional` mistake in production code, covered
below as a dedicated pitfall. `[NUM]`

**How it works — the eager-evaluation cost, spelled out.** `orElse(T other)` takes an
already-evaluated value of type `T`. Java evaluates method arguments **before** the method is
invoked — this is ordinary Java argument evaluation, nothing `Optional`-specific — so
`opt.orElse(expensiveLookup())` calls `expensiveLookup()` on *every* invocation, whether `opt` is
present or empty, because the argument must exist before `orElse` can even be called. Contrast
`orElseGet(Supplier<? extends T> supplier)`: the argument is a `Supplier` reference — creating it
costs nothing beyond a lambda-metafactory-produced object (or, since Java 21, potentially zero
extra objects if the JIT inlines and scalar-replaces it) — and `orElseGet`'s *body* only invokes
`supplier.get()` inside the `if (!isPresent())` branch. The arithmetic: if a QuizStakes wallet
lookup falls back to a database read costing an average 8ms (a plausible `FundsLedger` read under
light load) and 90% of lookups hit the cache and are present, `orElse(fundsLedger.readBalance
(clientId))` pays that 8ms on **every single call, present or not** — a 90% wasted cost — while
`orElseGet(() -> fundsLedger.readBalance(clientId))` pays it only on the 10% of calls that are
actually empty. Over the platform's card-deposit volume of 95k/day, that is the difference between
roughly 760,000 wasted 8ms database reads a day (`orElse`, 90% of 95k × 8ms ≈ 684 seconds of pure
waste) and zero (`orElseGet`). `[NUM]`

**D-105**, embedded here because this is the point in the explanation where the reader needs the
full picture of all five siblings side by side, including `ifPresentOrElse` and `or` which are
covered individually below:

| Method | Argument type | Evaluated when | Cost when value present | Returns on empty | QuizStakes case |
|---|---|---|---|---|---|
| `orElse` | `T` (already-evaluated value) | Always, before the call | The argument's full construction cost, wasted | The argument, unchanged | `bonus.orElse(Money.ZERO)` — a constant default, safe because `Money.ZERO` is free to build |
| `orElseGet` | `Supplier<? extends T>` | Only if empty | Zero (supplier never invoked) | `supplier.get()`'s result | `wallet.orElseGet(() -> fundsLedger.readBalance(clientId))` — a database fallback, deferred because it costs a round-trip |
| `orElseThrow` | `Supplier<? extends X extends Throwable>` (or no-arg for `NoSuchElementException`) | Only if empty | Zero (supplier never invoked) | Never returns — throws | `restriction.orElseThrow(() -> new RestrictedActionException(clientId, "STAKE_BLOCKED"))` — absence is not a valid outcome; the caller must not proceed |
| `ifPresentOrElse` | Two functional args: `Consumer<? super T>`, `Runnable` | Whichever branch applies | The consumer's cost | The runnable's cost | notify the client on a present bonus, log a compliance audit event when there is none — genuine two-branch case, no return value in either arm |
| `or` | `Supplier<? extends Optional<? extends T>>` | Only if empty | Zero | Another `Optional`, possibly itself empty | `cache.or(() -> database.lookup(clientId))` — a fallback **lookup**, not a fallback value; the result is still wrapped |

**D-105** — `orElse` vs `orElseGet` vs `orElseThrow`

**Example.**

```java
public final class WalletBalanceResolver {

    private final Map<ClientId, Money> hotCache;
    private final FundsLedger fundsLedger;

    public WalletBalanceResolver(Map<ClientId, Money> hotCache, FundsLedger fundsLedger) {
        this.hotCache = hotCache;
        this.fundsLedger = fundsLedger;
    }

    // orElse: the fallback is a constant, no work to defer
    public Money bonusOrZero(Optional<Bonus> maybeBonus) {
        return maybeBonus.map(Bonus::remainingAmount).orElse(Money.ZERO);
    }

    // orElseGet: the fallback does work, so it must be deferred
    public Money resolveBalance(ClientId clientId) {
        return Optional.ofNullable(hotCache.get(clientId))
                .orElseGet(() -> fundsLedger.readBalance(clientId));
    }

    // orElseThrow: absence is a compliance violation, not a value to default
    public void assertNotBlocked(ClientRestrictions restrictions, RestrictionType type) {
        restrictions.findActive(type)
                .ifPresent(r -> {
                    throw new RestrictedActionException(restrictions.clientId(), type);
                });
    }
}
```

**The gotcha.** `orElse(expensiveCall())` compiles cleanly, produces the correct value, and passes
every unit test that only checks the *result* — the defect is purely a performance one, invisible
until the expensive call is something with a side effect (an audit-log write on every
`resolveBalance` call, executed even for cache hits) or something slow enough to show up in a
latency histogram. **Pitfall:** teams that migrate from `orElse` to `orElseGet` purely by
search-and-replace regret it the other way: `orElseGet(() -> Money.ZERO)` is a pointless lambda
allocation for a value that was already free — use `orElse` when the value genuinely costs
nothing to construct, and reserve the lambda ceremony for cases where deferral matters.

> **`orElse` evaluates its argument unconditionally before the presence check even happens;
> `orElseGet` defers its supplier to the empty branch only; `orElseThrow` defers and then never
> returns — choose based on whether the fallback is free, expensive, or invalid.**

#### `ifPresentOrElse` for the genuine two-branch case

- **Mechanism.** `ifPresentOrElse(Consumer<? super T> action, Runnable emptyAction)`, added in
  Java 9, is the only method in the family with no return value in either branch — it exists
  because before it, the two-branch void case had no clean expression: you either wrote
  `if (opt.isPresent()) { ... } else { ... }` (back to the imperative style the whole discipline
  exists to avoid) or contorted `map`/`orElseGet` into doing side effects they were not designed
  for.
- **Gotcha:** it is tempting to reach for `ifPresentOrElse` when you actually want a *value* back
  from both branches — resist it. `ifPresentOrElse` returns `void`; if both branches need to
  produce a `Money` or a `ClientProfileView`, that is `map(...).orElseGet(...)`, not
  `ifPresentOrElse`.

  ```java
  clientRepository.findById(clientId).ifPresentOrElse(
          client -> notificationService.sendBonusAlert(client, bonus),
          () -> auditLog.record("bonus alert skipped: client not found for " + clientId));
  ```

> **`ifPresentOrElse` is for the void two-branch case only — one action for presence, one
> `Runnable` for absence, no return value from either.**

#### `or(Supplier)` for a fallback lookup chain

- **Mechanism.** `or(Supplier<? extends Optional<? extends T>> supplier)`, also Java 9, is the
  only member of the family whose supplier returns another `Optional<T>` rather than a raw `T`.
  That makes it the correct tool for chaining **lookups that might themselves fail**, not values
  that are guaranteed to exist once you fall back — a cache-then-database-then-give-up chain is
  exactly this shape, because the database step can also come back empty.
- **Gotcha:** `or` is lazy exactly like `orElseGet` — the supplier only runs if the receiver is
  empty — but it is easy to reach for `orElseGet` instead and then discover the "fallback" value
  you wanted was itself another `Optional`, forcing an awkward `.orElseGet(() ->
  fundsLedger.tryReadBalance(clientId).orElse(Money.ZERO))` double-unwrap. `or` chains cleanly
  instead:

  ```java
  public Optional<Money> resolveBalanceOrEmpty(ClientId clientId) {
      return Optional.ofNullable(hotCache.get(clientId))
              .or(() -> fundsLedger.tryReadBalance(clientId))   // Optional<Money>, may be empty
              .or(() -> Optional.of(Money.ZERO));                // last-resort default, still an Optional
  }
  ```

> **`or` chains `Optional`-returning fallbacks lazily; reach for it instead of `orElseGet` the
> moment your fallback is itself a lookup that can fail, not a guaranteed value.**

---

### `Optional` inside a stream: `.map(this::find).flatMap(Optional::stream)`

**Mental model first.** `Optional` and `Stream` are the same shape at two different sizes —
`Optional<T>` is a stream of zero-or-one elements that never got to call itself one, and
`Optional::stream` is the bridge that lets you treat it that way. Once you see `Optional<T>` as
"a `Stream<T>` capped at one element," the combinator `.flatMap(Optional::stream)` stops looking
like a trick and starts looking like the obvious way to drop the empty results out of a stream of
lookups.

**Why it exists.** Before `Optional.stream()` (Java 9), filtering a `Stream<Optional<T>>` down to
present values and unwrapping them required either `.filter(Optional::isPresent).map(Optional
::get)` — the exact `isPresent`+`get` pattern the discipline forbids, now smuggled into stream
operations where it is easier to miss in review — or a manual loop. `Optional.stream()` closes
that gap: it returns a `Stream<T>` containing the single value if present, or `Stream.empty()` if
not, which is precisely the shape `flatMap` wants.

**When to reach for it, and when not.** Reach for `.map(this::find).flatMap(Optional::stream)`
whenever the pipeline needs to look something up per-element and silently skip elements with no
answer. Do not reach for it when an absent lookup is itself meaningful (an error, a compliance
flag) — silently dropping it there hides information the caller needed; use `orElseThrow` inside
the `map` step instead, or restructure so the absence surfaces as a separate collection.

**How it works.** `Optional<T>.stream()`'s actual implementation (from `java.util.Optional`,
stable since Java 9) is:

```java
public Stream<T> stream() {
    if (!isPresent()) {
        return Stream.empty();
    } else {
        return Stream.of(value);
    }
}
```

Feeding that into `Stream<Optional<T>>.flatMap(Optional::stream)` means each element of the outer
stream is replaced by either zero elements (empty `Optional`) or one (present `Optional`), and
`flatMap`'s own mechanism — building one `AbstractPipeline` sink stage per source element and
concatenating their outputs — does the flattening. The net effect: a `Stream<Optional<T>>` of
size *n* becomes a `Stream<T>` of size ≤ *n*, with every absence silently and correctly dropped,
in one pass, with no intermediate `List` materialised.

**Example.** QuizStakes settling a batch of quiz rounds: given a list of `RoundId`s from the Quiz
Engine's `SettleStake` callback, look up each round's open `Reservation` and collect only the ones
that are still open (a round already voided or settled independently has no open reservation to
act on):

```java
public List<Reservation> findOpenReservations(List<RoundId> roundIds,
                                               ReservationRepository reservationRepository) {
    return roundIds.stream()
            .map(reservationRepository::findOpenByRoundId)   // Stream<Optional<Reservation>>
            .flatMap(Optional::stream)                        // Stream<Reservation>, absences dropped
            .toList();
}
```

**The gotcha.** `.flatMap(Optional::stream)` and `.filter(Optional::isPresent).map(Optional
::get)` produce identical output, so a reviewer skimming for "no `isPresent`+`get`" can miss the
filter-then-get form entirely because the two calls are split across a `filter` and a `map` and
no longer look like the forbidden pair. **Pitfall:** grep for `Optional::isPresent` and
`Optional::get` as method references, not just the instance-method call syntax — both forms leak
the same anti-pattern into stream pipelines.

> **`Optional.stream()` turns a zero-or-one value into a zero-or-one-element `Stream`, which is
> exactly the shape `flatMap` needs to drop absent lookups out of a pipeline in one pass.**

---

### Spring Data: `findById` versus `getReferenceById` — a different contract, the same shape

**Mental model first.** Both methods hand you something that *looks* like a `Client` object, but
one is a fully-loaded row and the other is a promise written on the back of a napkin — a proxy
that has not asked the database anything yet and will only find out whether the row exists the
moment you touch a real field on it.

**Why it exists.** `getReferenceById` (the Spring Data JPA 3.x name for the older
`getOne`/`getById`) exists to let you attach an association **without paying for a `SELECT`** —
Hibernate's `EntityManager.getReference` returns an uninitialized proxy purely so that, for
example, setting `reservation.setClient(clientRepository.getReferenceById(clientId))` can write
the foreign key without ever loading the `Client` row. `findById` exists for the ordinary case:
you actually need the client's data, so Spring Data issues the `SELECT` immediately and hands you
`Optional<Client>` because the row might genuinely not exist.

**When to reach for it, and when not.** Reach for `getReferenceById` only when you already know
the ID is valid (it came from a foreign key you are about to write, not from user input) and you
will never read a field off the returned object other than its ID. Reach for `findById` in every
other case — anywhere the row's existence is actually in question, which in QuizStakes is almost
everywhere a `ClientId` arrives from outside the process boundary (an API request, a webhook
callback, a message off a queue).

**How it works.** `findById` returns `Optional<Client>` — a container the caller must handle
before ever touching a `Client` field, so a missing row surfaces as an empty `Optional` at the
exact call site that looked it up. `getReferenceById` returns `Client` directly — no `Optional`
at all — but that `Client` is a CGLIB or bytecode-generated proxy subclass with every real field
uninitialised; the first access to any field **other than the identifier** triggers Hibernate to
issue the deferred `SELECT`, and if the row does not exist, that access throws
`jakarta.persistence.EntityNotFoundException` — not at the point you obtained the reference, but
at some arbitrary later point, possibly in a completely different method or even a different
transaction if the proxy escaped its `Session`. `[TRAP]`

`Optional` was designed to make "this might not exist" a compile-time-visible, immediate
concern; `getReferenceById` reintroduces exactly the "check now, find out later" hazard `Optional`
exists to prevent, and it does so **without** returning `Optional` at all — the two methods have
the same declared return type shape (`Client`, unwrapped, for `getReferenceById`) but opposite
failure timing.

**Example.**

```java
public interface ClientRepository extends JpaRepository<Client, ClientId> {
    // inherited from JpaRepository — no declaration needed
    // Optional<Client> findById(ClientId id);
    // Client getReferenceById(ClientId id);
}

@Service
public final class ReservationService {

    private final ClientRepository clientRepository;
    private final ReservationRepository reservationRepository;

    public ReservationService(ClientRepository clientRepository,
                               ReservationRepository reservationRepository) {
        this.clientRepository = clientRepository;
        this.reservationRepository = reservationRepository;
    }

    // Correct use of getReferenceById: the clientId is already validated upstream by the
    // Quiz Engine's ReserveStake call, and we never read a field off client here.
    @Transactional
    public Reservation createReservation(ClientId clientId, RoundId roundId, Money stake) {
        Client clientRef = clientRepository.getReferenceById(clientId); // no SELECT issued
        Reservation reservation = new Reservation(roundId, clientRef, stake);
        return reservationRepository.save(reservation);
    }

    // Correct use of findById: the clientId comes from an inbound API request and its
    // existence is genuinely in question.
    public ClientProfileView loadProfile(ClientId clientId) {
        Client client = clientRepository.findById(clientId)
                .orElseThrow(() -> new RestrictedActionException(clientId, "CLIENT_NOT_FOUND"));
        return ClientProfileView.from(client);
    }
}
```

**The gotcha.** **Pitfall:** calling `getReferenceById` with an ID that turns out not to exist,
then reading `client.getEmailAddress()` three services downstream, throws
`EntityNotFoundException` at that unrelated call site — a stack trace that points nowhere near the
actual mistake. The fix is the rule above: only use `getReferenceById` on an ID you already trust,
and only to write a foreign key, never to read data. `[X-REF 08]` the transactional-session
mechanics behind why the proxy can even throw lazily — and why it must be accessed inside the
same persistence context that produced it, or you get `LazyInitializationException` on top of the
`EntityNotFoundException` risk — are guide 08's territory (Spring Data JPA).

> **`findById` returns `Optional<Client>` and fails fast at the lookup site; `getReferenceById`
> returns an unwrapped, unvalidated proxy and fails lazily at first field access — same return
> shape's absence of `Optional`, opposite failure timing.**

#### Jackson: serialising an `Optional` field

- **Mechanism.** Jackson has no built-in knowledge of `java.util.Optional` — it is a
  `java.util` type, not a Jackson type, so without `com.fasterxml.jackson.datatype:
  jackson-datatype-jdk8` registered, Jackson serialises `Optional<String>` the way it serialises
  any POJO with no recognised shape: by reflecting over its declared fields, which for the
  historical `Optional` implementation surfaces as `{"present":true,"empty":false}` (field names
  vary slightly across JDK/Jackson version combinations, but the shape — a JSON object describing
  the `Optional`'s internal state rather than its payload — is consistent). With
  `jackson-datatype-jdk8` registered on the `ObjectMapper`, Jackson treats `Optional<T>` as a
  first-class supported type: a present value serialises as the unwrapped `T` directly, and an
  empty `Optional` serialises as JSON `null` (or is omitted entirely if the field also carries
  `@JsonInclude(JsonInclude.Include.NON_ABSENT)`). `[TRAP]` `[RESEARCH]` **Unverified:** the exact
  reflected field names Jackson emits without the module (`present`/`empty` versus only `present`)
  vary by JDK minor version and by whether Jackson's `BeanDescription` picks up `isEmpty()` as a
  getter; confirm the precise output on the project's actual JDK and Jackson versions before
  quoting field names in a bug report, rather than trusting a fixed shape here.
- **Gotcha:** Spring Boot's auto-configuration registers `jackson-datatype-jdk8` for you as long
  as it is on the classpath (`spring-boot-starter-json` pulls it in transitively as of Boot 2.x
  and later) — the trap is almost always a hand-rolled `ObjectMapper` built with `new
  ObjectMapper()` outside Spring's autoconfiguration, in a batch job or a Kafka consumer, that
  never registers the module and silently serialises `Optional<String> nationalInsuranceNumber`
  as an internal-state object instead of the value or `null`.

  ```java
  public record ClientComplianceDto(ClientId clientId, Optional<String> nationalInsuranceNumber) { }

  // Wrong: hand-built mapper, no jdk8 module — emits internal Optional shape, not the value
  ObjectMapper mapper = new ObjectMapper();

  // Right: register the module explicitly wherever Spring's autoconfiguration is bypassed
  ObjectMapper mapper = new ObjectMapper().registerModule(new Jdk8Module());
  ```

> **Without `jackson-datatype-jdk8`, `Optional` serialises as its own internal state; with it,
> a present value unwraps to the raw JSON value and an empty one becomes `null` (or is omitted
> with `@JsonInclude(NON_ABSENT)`).**

---

### `Optional` as a builder argument or a constructor parameter: the anti-pattern

**Mental model first.** An `Optional<Money>` constructor parameter does not make the constructor
easier to call — it makes it *harder*, because now the caller must first construct an `Optional`
just to hand it to you, when they already knew, at the call site, whether they had a value.
`Optional` on a parameter is a solution walking backwards past the problem it was built to solve.

**Why it exists (as folklore).** The anti-pattern usually arrives by analogy: "the return type
rule made `findById` nicer to call, so an `Optional<Money>` builder argument for an optional
discount must be nicer too." The analogy fails because the two positions are not symmetric — a
return type is produced by the callee, who genuinely does not know in advance whether it will
have an answer; a parameter is supplied by the caller, who already knows.

**When to reach for it, and when not.** Never reach for it. The alternative is always available
and always cheaper for the caller: an **overload** that omits the parameter (defaulting
internally), or a **builder method** that is only called when the value exists. `[TRAP]`

**How it works — the caller-side tax.** Compare the two call sites directly. With an `Optional`
parameter, every caller who has a plain `Money` must first wrap it:

```java
// Anti-pattern: Optional as a constructor parameter
public record StakeIntent(ClientId clientId, RoundId roundId, Money stake,
                           Optional<Money> promotionalOverride) { }

// Caller with no override must still construct Optional.empty()
StakeIntent intent = new StakeIntent(clientId, roundId, stake, Optional.empty());

// Caller with an override must wrap it just to hand it over
StakeIntent intentWithOverride = new StakeIntent(clientId, roundId, stake,
        Optional.of(discountedStake));
```

Against the overload alternative, neither caller pays a wrapping tax:

```java
// Correct: two constructors (or a builder with a defaulted field), no Optional in sight
public record StakeIntent(ClientId clientId, RoundId roundId, Money stake, Money promotionalStake) {

    public StakeIntent(ClientId clientId, RoundId roundId, Money stake) {
        this(clientId, roundId, stake, stake); // no override: promotional stake equals the raw stake
    }
}

StakeIntent intent = new StakeIntent(clientId, roundId, stake);
StakeIntent intentWithOverride = new StakeIntent(clientId, roundId, stake, discountedStake);
```

**The gotcha.** **Pitfall:** the `Optional`-parameter version also breaks records' canonical
constructor validation cleanly — you now need a null-check on the `Optional` reference itself
*and* a decision about what an empty `Optional` versus a present one containing a `null` `Money`
(should that even compile?) means, doubling the invariant surface for zero benefit. The overload
form has exactly one invariant to validate: is `Money` non-null.

> **`Optional` earns its keep only at a return type, where the callee genuinely does not know the
> answer in advance; on a parameter, the caller already knows, so wrapping it in `Optional` only
> moves the decision, it never simplifies it — use an overload or a defaulted builder field
> instead.**

---

### The four absence strategies compared

**Mental model first.** "How do I represent nothing?" has exactly four answers in a Java
codebase, and they sit on two independent axes: does the compiler check you, and does the
strategy travel across a process boundary. Seeing all four on one table stops the debate from
being "`Optional` versus `null`" (a false binary) and turns it into "which two axes does this
call site actually need."

**Why it exists.** Each strategy was adopted to fix a specific failure mode of the others:
nullability annotations (`@Nullable`/`@NonNull` plus a checker like NullAway) arrived because
`Optional` cannot be retrofitted onto every existing field and parameter in a large codebase
without a rewrite; the null-object pattern predates `Optional` entirely (it is a Gang-of-Four
pattern from 1994) and exists for call sites that want to skip the absence check altogether by
making the absent case behave like a harmless no-op object; exceptions exist because some
absences are not merely "no value" but "an operation that must not proceed."

**When to reach for it, and when not.** `[X-REF 03]` the full nullability-annotation and
NullAway toolchain — build-time enforcement configuration, annotation processor wiring, and how
strict mode differs from lenient mode — is guide 03's territory (Java core); the mechanism
paragraph below gives enough to answer an interview question about it without sending you there
empty-handed.

- **`Optional`** — a return type where absence is a normal, expected outcome the immediate caller
  must handle inline. `ClientRepository.findById`.
- **Nullability annotations + NullAway** — fields, parameters, and existing large codebases where
  retrofitting `Optional` everywhere is not realistic; the annotation documents intent and
  NullAway (a Java-source static analyser built on Error Prone, from Uber) fails the *build* on a
  provably unguarded dereference of a `@Nullable`-annotated value, catching a class of bug at
  compile time that `Optional` catches only at the specific boundary it wraps.
- **The null-object pattern** — a call site that would otherwise need to null-check (or
  `Optional`-check) on every use, where a "do-nothing" implementation of the same interface is
  cheap and correct: `Restriction.NONE` implementing `blocksAction()` as always returning `false`
  removes every caller's need to ask "is there a restriction" at all — they just call
  `restriction.blocksAction()` unconditionally.
- **An exception** — absence that is not a value at all but a precondition failure: a
  `RestrictedActionException` when `ClientRestrictions.findActive(STAKE_BLOCKED)` finds an active
  block and the caller must not proceed under any circumstances. This is not really "representing
  absence" — it is refusing to return a value because the situation makes returning one wrong.

**How it works — the comparison.**

**D-106**, embedded here at the point of explanation:

| | `Optional` | Nullability annotations + NullAway | Null-object pattern | Exception |
|---|---|---|---|---|
| Enforced by the compiler | No — a hint only; nothing stops a field or parameter | Partially — NullAway fails the *build*, not the language, on a provable violation; unannotated third-party code is a blind spot | No — relies on every implementation actually returning the null-object, never `null` | Yes, for checked exceptions (the compiler forces a catch or a `throws` clause); unchecked exceptions are not enforced at all |
| Allocation cost | One wrapper object per non-empty value (`Optional.of`); `Optional.empty()` is a shared singleton, zero cost | Zero — annotations are compile-time-only metadata, erased before bytecode | Zero extra per call — the null-object instance is typically a shared singleton, same as `Optional.empty()` | The `Throwable` construction cost, plus a stack-trace fill unless suppressed — the most expensive of the four per occurrence |
| Works in a field | No (see the rule set above) | Yes — `@Nullable Money pendingBonus` is the idiomatic field shape | Yes — `Restriction restriction = Restriction.NONE;` is a normal field assignment | N/A — a field cannot "throw" on read; this axis does not apply |
| Works across an API boundary | Yes, but only within the JVM — `Optional` is not designed to cross a serialisation boundary and most JSON/RPC contracts (see the Jackson leaf above) unwrap it before it leaves the process | Yes, in source form only — annotations do not survive into a wire format or a different language's client | Yes — the null-object's *behaviour* crosses the boundary as ordinary data (e.g. an empty-but-valid restriction list), but the "this represents absence" intent does not travel with it | Yes — an exception (or its HTTP-status/error-code equivalent) is the standard way absence-as-failure crosses a REST or RPC boundary |
| Tooling support | Excellent — first-class JDK type, IDE-aware, `Optional`-specific inspections in IntelliJ and Error Prone | Good, but ecosystem-fragmented — JSR-305 `@Nullable`, JSpecify (the emerging unified standard), Android's, and Spring's own `@Nullable` are all slightly different types that do not always compose | Weak — nothing distinguishes a null-object instance from a "real" one at the type level; a reviewer must know the convention | Excellent — exceptions are a core language feature with full IDE, debugger, and stack-trace support |
| Failure mode when ignored | `NoSuchElementException` on an unguarded `.get()` — same *category* of runtime crash `Optional` was built to prevent, just later and rarer | A `NullPointerException` at the actual unguarded dereference, exactly as if the annotation had never been added — the annotation only helps if the build enforces it | Silent wrong behaviour — a caller that assumed the null-object convention, but calls a method the null-object implements as a no-op when it actually needed the real behaviour, gets no exception at all, just an incorrect outcome | An uncaught exception propagates and typically aborts the request/transaction — the loudest of the four failure modes, which is often exactly the point |

**D-106** — Four absence strategies compared

**Example.** All four strategies applied to the same fact — "does this client have an active
stake restriction" — so the tradeoffs are visible side by side:

```java
public final class ClientRestrictions {

    private final List<Restriction> activeRestrictions;

    public ClientRestrictions(List<Restriction> activeRestrictions) {
        this.activeRestrictions = List.copyOf(activeRestrictions);
    }

    // Strategy 1: Optional — caller must handle absence inline, at the call site
    public Optional<Restriction> findActive(RestrictionType type) {
        return activeRestrictions.stream()
                .filter(r -> r.type() == type)
                .findFirst();
    }

    // Strategy 4: exception — absence is not acceptable, the caller must not proceed
    public void assertNotBlocked(RestrictionType type) {
        findActive(type).ifPresent(r -> {
            throw new RestrictedActionException(r.clientId(), type);
        });
    }
}

// Strategy 3: null-object — every caller can call blocksAction() unconditionally
public sealed interface Restriction permits ActiveRestriction, NoRestriction {
    boolean blocksAction();

    Restriction NONE = new NoRestriction();
}

record NoRestriction() implements Restriction {
    @Override public boolean blocksAction() { return false; }
}

// Strategy 2: nullability annotation — a field, checked at build time by NullAway
public final class WalletSnapshot {
    private final Money cashAvailable;
    private final @Nullable Money pendingChargebackHold; // null means no hold, no wrapper needed

    public WalletSnapshot(Money cashAvailable, @Nullable Money pendingChargebackHold) {
        this.cashAvailable = cashAvailable;
        this.pendingChargebackHold = pendingChargebackHold;
    }
}
```

**The gotcha.** The four strategies are not mutually exclusive within one codebase, and that is
correct, not sloppy — the mistake is applying the wrong one to a given call site, not using more
than one strategy across a codebase. **Pitfall:** teams that adopt `Optional` as a blanket "ban
`null` everywhere" policy end up wrapping fields and parameters in `Optional` in violation of the
rule set above, when a `@Nullable` annotation would have been both cheaper and more idiomatic for
that position.

> **`Optional`, a nullability annotation, a null-object, and an exception are four answers to
> "how do I represent nothing," differentiated by whether the compiler checks it and whether it
> survives a process boundary — pick per call site, not as a single codebase-wide policy.**

#### `Optional.of(1).equals(Optional.of(1))` is `true`; `Optional.empty().equals(null)` is `false` `[PROVE]`

- **Mechanism.** Work both through `Optional`'s actual `equals` (stable since Java 8):

  ```java
  @Override
  public boolean equals(Object obj) {
      if (this == obj) {
          return true;
      }
      return obj instanceof Optional<?> other
              && Objects.equals(value, other.value);
  }
  ```

  For `Optional.of(1).equals(Optional.of(1))`: neither reference is the other object, so the
  `this == obj` short-circuit fails; `obj instanceof Optional<?>` succeeds because both sides are
  `Optional` instances; `Objects.equals(value, other.value)` then compares the *unwrapped*
  values — `Integer.valueOf(1)` against `Integer.valueOf(1)` — which is `true` both because
  `Integer.equals` compares by value and, for the specific value `1`, because both come from the
  `Integer` cache (`-128` to `127` are cached, so they are even the same reference). The overall
  result is `true`: `Optional.equals` **delegates entirely to the wrapped value's own `equals`**,
  which is exactly why two separately-constructed `Optional` instances wrapping equal values are
  themselves equal — `Optional` was designed to be usable as a `Map` key, a `Set` element, and a
  test-assertion target, all of which require this delegation.

  For `Optional.empty().equals(null)`: `this == obj` compares `Optional.empty()`'s singleton
  reference against the literal `null` — never equal, since `this` can never be `null` inside an
  instance method. Then `obj instanceof Optional<?>` — `instanceof` against a `null` operand is
  defined by the JLS to always evaluate to `false`, for any type on the right-hand side — so the
  `&&` short-circuits and `Objects.equals` is never even reached. The result is `false`.
- **Gotcha:** the two results together are the entire point of the type's existence, and stating
  only one of them misses it — `Optional.empty()` is a real, non-null object that is simply
  never equal to the absence-value `null` it was invented to replace; conflating "empty
  `Optional`" with "`null`" in an `equals` check is exactly the confusion `Optional` exists to
  eliminate. **Pitfall:** `assertThat(maybeClient).isEqualTo(null)` on an empty `Optional<Client>`
  fails the assertion, surprising an engineer who mentally treats "empty" and "null" as
  synonyms — they are not, and the `equals` contract enforces that distinction mechanically.

> **`Optional.equals` delegates to the wrapped value's `equals` when both sides are non-empty
> `Optional`s, and always returns `false` against a bare `null` because `instanceof` against
> `null` is always `false` by JLS definition — an empty `Optional` is a real object, never
> interchangeable with the absence of one.**

#### `Optional` in a hot loop: one allocation per call `[NUM]` `[X-REF 06]`

- **Mechanism.** `Optional.of(value)` and `Optional.ofNullable(value)` (when the argument is
  non-null) both allocate a new `Optional` instance on every call — there is no cache, no
  interning, unlike `Optional.empty()` which returns the same shared `EMPTY` singleton every
  time. In QuizStakes terms: the Quiz Engine's `ReserveStake` path runs at 1,200 reservations/sec
  at peak (from the platform's stake-reservation volume), and if the reservation lookup on that
  hot path returns `Optional<Reservation>` on every call, that is up to 1,200 new `Optional`
  wrapper objects allocated per second, purely for the wrapping — on top of whatever the
  `Reservation` object itself costs. `[NUM]` In practice this rarely shows up as measurable
  garbage-collector pressure, because the JIT's escape analysis can prove that an `Optional`
  which never leaves the method that created it (never stored in a field, never returned, never
  passed somewhere it might escape) does not need heap allocation at all — the JIT performs
  **scalar replacement**, breaking the object into its constituent fields and keeping them in
  registers or on the stack, exactly the way it does for any other short-lived, non-escaping
  object. `[X-REF 06]` the general mechanics of escape analysis and scalar replacement — how the
  JIT proves non-escape, the compilation tiers at which it kicks in, and the JVM flags that
  disable it for diagnosis — are guide 06's territory (JVM internals).
- **Gotcha:** escape analysis is a JIT optimisation, not a language guarantee — it depends on the
  method being hot enough to reach C2 compilation, on the `Optional` genuinely never escaping (a
  method that stores it in a field or returns it defeats the analysis immediately), and on the
  specific JVM and flags in use. **Pitfall:** "the JIT removes `Optional` allocations, so hot-path
  allocation concerns are theoretical" is true often enough to be dangerous folklore — confirm it
  for a specific hot path with an allocation profiler (async-profiler's allocation mode, or JFR's
  `jdk.ObjectAllocationSample` event) rather than assuming it, because a method that looks
  non-escaping in isolation can start escaping the moment a caller changes to store the result.

> **`Optional.of`/`Optional.ofNullable` allocate one wrapper object per non-empty call — usually
> free in practice because escape analysis lets the JIT scalar-replace a non-escaping `Optional`,
> but that is a JIT optimisation to verify with a profiler on a genuine hot path, never an
> assumption to build a performance argument on unmeasured.**

---

## Pitfalls

### Reaching for `orElse(expensiveCall())` because it "reads the same" as `orElseGet`

**Wrong**

```java
public Money resolveBalance(ClientId clientId, Map<ClientId, Money> hotCache) {
    return Optional.ofNullable(hotCache.get(clientId))
            .orElse(fundsLedger.readBalance(clientId)); // runs on every call, cache hit or not
}
```

**Right**

```java
public Money resolveBalance(ClientId clientId, Map<ClientId, Money> hotCache) {
    return Optional.ofNullable(hotCache.get(clientId))
            .orElseGet(() -> fundsLedger.readBalance(clientId)); // runs only on a cache miss
}
```

**Why people believe it:** `orElse` and `orElseGet` produce byte-for-byte identical results in
every test that only asserts the return value, because the two methods only diverge in *when*
the argument runs, never in *what* it returns — the divergence is purely a cost defect, invisible
until someone puts a counter or a `Thread.sleep` inside the fallback and notices it fires on
every call.

### Treating `getReferenceById` as a cheaper `findById`

**Wrong**

```java
public ClientProfileView loadProfile(ClientId clientId) {
    Client client = clientRepository.getReferenceById(clientId); // no existence check yet
    return ClientProfileView.from(client); // throws EntityNotFoundException here instead,
                                            // deep inside ClientProfileView.from, far from
                                            // where clientId actually came from
}
```

**Right**

```java
public ClientProfileView loadProfile(ClientId clientId) {
    Client client = clientRepository.findById(clientId)
            .orElseThrow(() -> new RestrictedActionException(clientId, "CLIENT_NOT_FOUND"));
    return ClientProfileView.from(client);
}
```

**Why people believe it:** both methods return something typed `Client`, both compile identically
at every call site, and `getReferenceById` genuinely is cheaper when the ID is already known-good
— the trap is treating "cheaper" as "always fine to use," when the two methods differ precisely
on the one property (does the row exist) that a caller with an unverified ID actually needs
checked immediately.

### Wrapping a builder or constructor argument in `Optional` "to make it optional"

**Wrong**

```java
public record StakeIntent(ClientId clientId, RoundId roundId, Money stake,
                           Optional<Money> promotionalOverride) { }

StakeIntent intent = new StakeIntent(clientId, roundId, stake, Optional.empty());
```

**Right**

```java
public record StakeIntent(ClientId clientId, RoundId roundId, Money stake, Money promotionalStake) {
    public StakeIntent(ClientId clientId, RoundId roundId, Money stake) {
        this(clientId, roundId, stake, stake);
    }
}

StakeIntent intent = new StakeIntent(clientId, roundId, stake);
```

**Why people believe it:** the return-type rule genuinely does make `findById` nicer for its
caller, so it feels like the same trick should make an optional constructor argument nicer too —
the asymmetry (callee doesn't know vs. caller already knows) is easy to miss because both
positions use the word "optional" in the same intuitive sense.

### Serialising a hand-built `ObjectMapper` without `Jdk8Module`

**Wrong**

```java
ObjectMapper mapper = new ObjectMapper();
String json = mapper.writeValueAsString(
        new ClientComplianceDto(clientId, Optional.of("AB123456C")));
// {"clientId":{...},"nationalInsuranceNumber":{"present":true}}  — the value is gone
```

**Right**

```java
ObjectMapper mapper = new ObjectMapper().registerModule(new Jdk8Module());
String json = mapper.writeValueAsString(
        new ClientComplianceDto(clientId, Optional.of("AB123456C")));
// {"clientId":{...},"nationalInsuranceNumber":"AB123456C"}
```

**Why people believe it:** Spring Boot registers the module automatically almost everywhere, so
most engineers never see the failure mode — it only shows up in a batch job, a Kafka consumer, or
a test harness that builds its own `ObjectMapper` outside Spring's autoconfiguration, and by then
the missing module is easy to overlook as the cause.

---

## Cheat sheet

| Situation | Use | Never use |
|---|---|---|
| Method might have no answer | `Optional<T>` return type | `null` return, sentinel value |
| Entity field, DTO field | Plain nullable type + `@Nullable` | `Optional<T>` field |
| Constructor/builder argument that's sometimes absent | Overload, or a defaulted builder field | `Optional<T>` parameter |
| Collection element / map value that might be absent | Omit the entry | `Optional<T>` element/value |
| Fallback is a free constant | `orElse(Money.ZERO)` | `orElseGet(() -> Money.ZERO)` |
| Fallback does work (DB call, computation) | `orElseGet(() -> ...)` | `orElse(expensiveCall())` |
| Absence is invalid, must abort | `orElseThrow(() -> new X(...))` | returning a silent default |
| Void action on presence, different void action on absence | `ifPresentOrElse(consumer, runnable)` | `if/else` with `isPresent()`/`get()` |
| Fallback is itself a lookup that can fail | `or(() -> otherOptional)` | nested `orElseGet` unwrapping |
| Dropping absent lookups out of a stream | `.map(this::find).flatMap(Optional::stream)` | `.filter(Optional::isPresent).map(Optional::get)` |
| Attach an association, ID already trusted, no field reads | `getReferenceById` | `findById` (needless `SELECT`) |
| ID's existence is genuinely in question | `findById` + `orElseThrow`/`orElse` | `getReferenceById` |
| Serialise `Optional` fields to JSON correctly | Register `Jdk8Module` | Hand-built `ObjectMapper` with no module |
| Every caller should skip an `if` check entirely | Null-object pattern | `Optional` + `.isPresent()` at every call site |
| Large legacy codebase, can't retrofit `Optional` everywhere | `@Nullable`/`@NonNull` + NullAway | Silent `null`, no annotation |
| `Optional.of(x).equals(Optional.of(y))` | Delegates to `x.equals(y)` | — |
| `Optional.empty().equals(null)` | Always `false` (`instanceof null` is `false`) | — |
| Hot-path `Optional` allocation concern | Profile with async-profiler/JFR first | Assume the JIT always removes it |

---

## Self-test

**Q1.** Why is `orElse(fundsLedger.readBalance(clientId))` a performance defect even when every
unit test asserting the returned `Money` value passes?

<details><summary>Answer</summary>

Because Java evaluates method arguments before the method call happens, `orElse`'s argument —
`fundsLedger.readBalance(clientId)` — runs on **every** invocation, whether the `Optional` is
present or empty, since the argument must already exist as a value before `orElse` can be called
at all. A unit test that only checks the returned value cannot distinguish this from
`orElseGet(() -> fundsLedger.readBalance(clientId))`, which defers the same call to the empty
branch only — the two produce identical results and only diverge in how many times the expensive
call actually runs, which is a cost defect invisible to a value-only assertion.

</details>

**Q2.** A `ClientRestrictions` field is declared `Optional<Restriction> activeStakeBlock`. Name
two concrete problems this causes beyond "it violates the rule set."

<details><summary>Answer</summary>

First, most JPA/Hibernate mappings do not support `Optional` on an entity field directly (Hibernate
6 added partial support, but it is narrower than a plain nullable column), so it either fails to
map, silently treats the field as if it were the raw type, or requires a custom converter that
a plain `@Nullable Restriction` field would never have needed. Second, it costs one extra
`Optional` wrapper allocation per instance that a `null` field or the null-object pattern would
avoid, and because a field-held `Optional` cannot be proven non-escaping the way a local one can,
it is not a candidate for JIT scalar replacement — the allocation is real, not eliminated.

</details>

**Q3.** Walk through why `getReferenceById(clientId)` on a non-existent `clientId` does not throw
immediately, and name exactly where it does throw.

<details><summary>Answer</summary>

`getReferenceById` returns a Hibernate-generated proxy subclass of `Client` with no fields
populated and no `SELECT` issued — it only knows the identifier it was asked for. Because the
method's declared return type is `Client`, not `Optional<Client>`, there is no absence signal at
the call site at all; the proxy is handed back unconditionally. The deferred `SELECT` only fires
the moment code accesses a field on the proxy other than its identifier (for example calling
`client.getEmailAddress()`), and if that `SELECT` finds no row, `EntityNotFoundException` is
thrown at that field-access point — which can be an entirely different method, service, or even
transaction from the one that originally called `getReferenceById`.

</details>

**Q4.** Rewrite this into the chain style and explain what changed: `Optional<Client> maybeClient
= clientRepository.findById(clientId); if (maybeClient.isPresent()) { auditLog.record(maybeClient
.get().id()); }`.

<details><summary>Answer</summary>

```java
clientRepository.findById(clientId)
        .map(Client::id)
        .ifPresent(auditLog::record);
```

The `isPresent()`/`get()` pair is replaced by a single expression where the absence-handling
obligation (simply doing nothing, here) sits next to the success path instead of being a separate
`if` block that a later refactor could accidentally split from its guard — for example, inserting
a line between the `isPresent()` check and the `get()` call that could throw before the
dereference is reached. The chain form makes that drift structurally impossible because there is
no gap between checking and using.

</details>

**Q5.** Why does `.flatMap(Optional::stream)` produce the exact same output as `.filter(Optional
::isPresent).map(Optional::get)`, and why is the first form still preferred?

<details><summary>Answer</summary>

`Optional.stream()` returns `Stream.of(value)` when present and `Stream.empty()` when absent;
feeding a `Stream<Optional<T>>` through `.flatMap(Optional::stream)` therefore replaces each
present `Optional` with its single unwrapped value and each empty one with nothing, which is
exactly what filtering to present elements and then unwrapping them achieves. The first form is
preferred because it never calls `Optional::isPresent` or `Optional::get` as a pair anywhere in
the source, which keeps a "no `isPresent`+`get`" code-review or static-analysis rule effective —
the filter-then-get form hides the same forbidden pair by splitting it across two stream stages,
which is easy for a reviewer to miss.

</details>

**Q6.** Prove that `Optional.of(1).equals(Optional.of(1))` is `true` by walking `Optional`'s
`equals` method, not by asserting the result.

<details><summary>Answer</summary>

`Optional.equals` first checks `this == obj`, which fails since these are two distinct `Optional`
instances. It then checks `obj instanceof Optional<?>`, which succeeds since both sides are
`Optional`. It finally evaluates `Objects.equals(value, other.value)`, comparing the two wrapped
`Integer` values `1` and `1` via `Integer.equals`, which compares by primitive value and returns
`true` (and for small integers like `1`, both references even come from the same cached `Integer`
instance, though that is incidental to the result). Because all three steps resolve to `true`,
the overall `equals` call is `true` — `Optional.equals` fully delegates to the wrapped value's own
`equals`.

</details>

**Q7.** Why is `Optional.empty().equals(null)` `false`, even though "empty" and "absent" sound
like the same idea as `null`?

<details><summary>Answer</summary>

`Optional.empty()` is a real, non-null object — the shared `EMPTY` singleton — and its `equals`
method checks `obj instanceof Optional<?>` against the argument. The JLS defines `instanceof`
against a `null` right-hand operand as always evaluating to `false`, for any type, so this check
fails immediately and short-circuits before `Objects.equals` is ever reached. The result is
`false` precisely because an empty `Optional` is a distinct, non-null representation of absence,
never interchangeable with the literal `null` it was designed to replace.

</details>

**Q8.** A hot loop processing stake reservations at 1,200/sec calls a method returning
`Optional<Reservation>` on every iteration. Should this be a performance concern? What would you
actually check before concluding either way?

<details><summary>Answer</summary>

Not automatically — if the `Optional` never escapes the calling method (never stored in a field,
never returned, never passed to something that retains it), the JIT's escape analysis can prove
it non-escaping once the method is hot enough to reach C2 compilation, and scalar-replace it into
its constituent fields with no heap allocation at all. But that is a JIT optimisation contingent
on the method actually being hot and the reference genuinely not escaping, not a language
guarantee, so the honest answer is to profile the specific hot path — with async-profiler's
allocation mode or JFR's `jdk.ObjectAllocationSample` event — rather than assume it is free or
assume it is expensive.

</details>

**Q9.** Compare the null-object pattern and `Optional` for representing "no active restriction."
Which one lets every caller skip the presence check entirely, and why does that matter?

<details><summary>Answer</summary>

The null-object pattern lets every caller skip the check: `Restriction.NONE` implements the same
interface as a real restriction, with `blocksAction()` returning `false`, so callers invoke
`restriction.blocksAction()` unconditionally with no branch at all. `Optional<Restriction>`
requires every caller to unwrap it — via `map`, `orElse`, or similar — before they can ask
anything about the restriction. This matters because the null-object pattern is the right choice
exactly when the "do nothing" behaviour is cheap, correct, and shared across all call sites; if
different callers need different absence behaviour (one throws, one defaults, one logs), that
divergence is exactly what `Optional`'s per-call-site handling is for, and the null-object pattern
would have to bake one specific "do nothing" behaviour into the shared instance instead.

</details>

**Q10.** Without `jackson-datatype-jdk8` registered, what does `Optional<String>
nationalInsuranceNumber` actually serialise as, and why does Spring Boot rarely surface this bug?

<details><summary>Answer</summary>

Jackson has no built-in understanding of `java.util.Optional`, so absent the module it reflects
over the type as an ordinary POJO and serialises its internal presence-tracking state — an object
describing whether a value is present — rather than the unwrapped value or `null`. Spring Boot
rarely surfaces this because `spring-boot-starter-json` pulls in `jackson-datatype-jdk8`
transitively and Spring's autoconfiguration registers it on the primary `ObjectMapper`
automatically; the bug only appears when some other part of the system — a batch job, a Kafka
consumer, a standalone test harness — constructs its own `ObjectMapper` outside that
autoconfiguration and never registers the module itself.

</details>

---

## Deferred

None.

---

**Leaves covered:** 2.6.1–2.6.12 (12 leaves)
**Leaves deferred:** none
**Diagrams included:** D-105, D-106
**Target version:** Java 21 LTS
**Lines:** 1069
