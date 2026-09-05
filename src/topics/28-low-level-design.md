# 28 — Low-Level Design Drills

Scope: the **object-oriented design / machine-coding round** — one class model plus working Java in
45–90 minutes, no distributed systems. This is not `22-system-design.md` or `27-high-level-design.md`:
those two are boxes-and-arrows across machines (services, queues, databases, replicas). This is one
process, one heap: which classes exist, who owns which invariant, what the public API looks like, and
whether the code you type actually compiles and runs. It is also not
`24-design-patterns-architecture.md`: 24 teaches the patterns themselves as mechanism (forces,
consequences, JDK proxy internals, SOLID as failure modes); this guide *applies* them under a clock,
on problems that were never designed to teach one pattern in isolation. If you cannot state why a
design in this file uses strategy instead of an `if/else` ladder, that gap is 24's, not this file's —
go read it first.

The failure mode this guide exists to fix: engineers who can recite SOLID and still produce, under
time pressure, a `ParkingLot` class with 400 lines, six responsibilities, and a `switch` on vehicle
type buried three methods deep — because knowing patterns in the abstract and *reaching for the right
one inside three minutes on an unfamiliar prompt* are different skills. LLD rounds are graded on the
second skill.

---

## 1. How to drill this file

Do **not** read a worked design straight through — reading a class diagram is not the same skill as
producing one from a blank page in 45 minutes with an interviewer watching.

1. Read only the **Prompt** line. Start a 45-minute timer (60–90 for the machine-coding variant, §16).
2. Design on paper or a whiteboard app first — no IDE. Class names, responsibilities, one or two key
   method signatures, the state machine if there is one. Then, if time remains, write the Java.
3. Read the section. Score yourself against the design, not against whether your code compiles —
   compiling is necessary but not sufficient; a compiling god class still fails the round.
4. Anything you missed that is a *pattern mechanism* (why strategy, why not inheritance, why the
   proxy can't see this) is `24-design-patterns-architecture.md`'s job to fix, not this file's — follow
   the cross-reference.
5. Second pass a week later, 30 minutes, no paper: state the class model and the fork out loud before
   touching a keyboard. If you can't, you memorised the diagram instead of the reasoning that produced
   it, and an interviewer who changes one requirement (add concurrency, add a new vehicle type) will
   catch that immediately.

---

## 2. The compressed LLD template

Eleven slots, in order. If a slot is empty at minute 30, that is where the round is lost — most
candidates spend 20 minutes writing code before slot 3 is even named.

| # | Slot | Output it must produce |
|---|---|---|
| 1 | Scope + explicit out-of-scope | 3–5 use cases with an actor; say what you are *not* building, out loud |
| 2 | Actors and use cases | Who initiates what — this is where hidden actors surface (an admin, a scheduler, a payment gateway) |
| 3 | Nouns → candidate classes, and rejections | Every noun in the prompt is a candidate; state which ones you merge or drop and why |
| 4 | Responsibilities + the invariant each class owns | One sentence per class: what must always be true while this class exists |
| 5 | Public API / interface signatures first | Method signatures before implementation — this is the actual contract under test |
| 6 | Core entities as records/sealed types | Immutable data first; behaviour attaches via methods or collaborators, not setters |
| 7 | State machine for any lifecycle | Legal-transition table if any entity has a status field |
| 8 | Concurrency and consistency boundary | What is shared across threads/requests, and the exact guard |
| 9 | Persistence boundary | In-memory now, behind a repository interface, so swapping to a DB later is not a rewrite |
| 10 | Extension test | Name the next 2 requirements and show where each lands, unprompted |
| 11 | What you deliberately did not build | Say it — an interviewer scores honesty about scope as much as coverage |

**Slot 5 before slot 6 is the trap most candidates get backwards.** Writing `class ParkingLot { Spot[]
spots; }` and then improvising methods produces an API shaped by whatever was convenient to implement.
Writing `Ticket park(Vehicle v)` and `Receipt unpark(Ticket t)` first forces you to decide what the
caller actually needs before you've committed to a data structure that might not support it.

**Slot 10, the extension test, is the single highest-scoring sentence in an LLD round**, exactly as
slot 7 is in `27-high-level-design.md`'s HLD template. Naming "if we add electric-vehicle spots with
charging, that's a new `SpotType` and a new pricing rule — zero changes to `ParkingLotService`" before
being asked proves the design is open for extension, not just correct for the stated case.

---

## 3. Forcing-function map — recognise the problem in three minutes

| Prompt shape | Looks like | Actually tests | The fork |
|---|---|---|---|
| "Design a `X` for a physical space with capacity" | Inventory management | Allocation strategy + concurrency on the free-resource pool | Central strategy object vs hardcoded rule |
| "Design a system with cars/cabins that move and respond to calls" | A queue of requests | Per-unit state machine + scheduling strategy + request dedup | One scheduler for the fleet vs each car self-scheduling |
| "Design a machine with buttons, coins, inventory" | A UI mock | Pure state machine correctness under invalid input | State pattern vs boolean-flag sprawl |
| "Design a system to lend/borrow physical or digital items" | CRUD | Entity vs unit-of-inventory modelling (the book vs the copy) | One class doing double duty vs two classes with different lifecycles |
| "Design a system to split shared costs among people" | Arithmetic | Rounding correctness + strategy selection + graph simplification | Naive pairwise settlement vs net-graph simplification |
| "Design a two-player board game" | A grid | Move legality without a type-switch god method; immutability of history | Polymorphic piece behaviour vs a central rules engine |
| "Design a component that throttles calls inside one process" | A counter | Same algorithm as `27 §4`'s rate limiter, but the fork is the concurrency primitive, not the network hop | Lock-based vs CAS/atomic |
| "Design a logging library" | `println` wrapper | Layered responsibility (logger → appender → formatter) + async ordering under contention | Synchronous per-call I/O vs buffered async with ordering guarantees |
| "Design an in-memory cache with a size bound" | A `HashMap` | Eviction policy as a pluggable interface + O(1) access-order tracking | Intrusive doubly linked list + map vs `LinkedHashMap` access-order mode |
| "Design a key-value store with transactions" | A `HashMap` with locks | Nested transaction semantics via an undo journal, not copy-on-write snapshots | Undo-log rollback vs shadow-copy commit |

**Trap:** solving the *visible* problem. "Design a parking lot" candidates spend 30 minutes on a
beautiful `Spot`/`Level` hierarchy and never mention that two attendants scanning license plates at
the same gate can double-assign the last compact spot — the concurrency fork (slot 8) is worth more
than the class diagram's elegance.

---

## 4. Design — parking lot

**Prompt:** design a multi-level parking garage that assigns spots to vehicles by type and charges on
exit.

**Clarifications to ask (and the answer to assume):**
- Vehicle types and spot types — are they 1:1 or can a car use a compact or a large spot? *Assume a
  compatibility rule: motorcycle → any, car → compact or large, bus → large only, and EV needs a
  charging-enabled spot regardless of size.*
- Multiple levels, or one? *Assume 5 levels, ~100 spots/level, mixed types.*
- Pricing — flat, per-hour, per-vehicle-type? *Assume per-hour, tiered by vehicle type, with a
  strategy object so it can change without touching allocation.*
- Payment — cash/card integration in scope? *Out of scope — return an amount due; assume it's paid.*
- Concurrency — one attendant terminal, or many gates issuing tickets concurrently? *Assume many gates
  — this is the whole point of the design.*
- What happens when full? *Return a `NoSpotAvailableException`/`Optional.empty()`, don't crash.*

**The fork:** spot allocation is a pluggable strategy (nearest-first, level-balancing, type-fallback)
kept out of `ParkingLotService`, pricing is a separate collaborator entirely — and the free-spot pool
is the one piece of mutable shared state that must be updated atomically, because two gates racing for
the last compact spot is the actual bug an interviewer is watching for, not the class names.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `ParkingLot` | Owns levels, exposes `park`/`unpark` | Exactly one `Ticket` per parked `Vehicle` at any time |
| `Level` | Owns a set of `Spot`s | A spot belongs to exactly one level |
| `Spot` | One physical space with type + state | State transitions only via CAS, never a bare setter |
| `SpotType` (enum) | `COMPACT, LARGE, HANDICAPPED, EV` | Compatibility rule lives here, not in `ParkingLot` |
| `Vehicle` | Immutable record: plate, type | — |
| `Ticket` | Immutable record: id, spot, vehicle, entryTime | Never mutated after issue; exit produces a `Receipt`, not a mutation |
| `SpotAllocationStrategy` (interface) | Picks a spot for a vehicle across levels | — |
| `PricingStrategy` (interface) | Computes amount due from a `Ticket` + exit time | — |
| Rejected: `Attendant` class | Adds no invariant — gates are just callers of `ParkingLotService` |
| Rejected: `Payment` class | Explicitly out of scope per clarifications |

**Java 21 code:**

```java
public sealed interface SpotType permits SpotType.Compact, SpotType.Large, SpotType.Handicapped {}
enum VehicleType { MOTORCYCLE, CAR, BUS }

record Vehicle(String plate, VehicleType type) {}

final class Spot {
    enum State { AVAILABLE, OCCUPIED }
    private final int id;
    private final VehicleType maxType;      // spot fits vehicles up to this size
    private final AtomicReference<State> state = new AtomicReference<>(State.AVAILABLE);

    boolean tryOccupy() { return state.compareAndSet(State.AVAILABLE, State.OCCUPIED); }
    void release() { state.set(State.AVAILABLE); }
    boolean fits(Vehicle v) { return v.type().ordinal() <= maxType.ordinal(); }
}
```

```java
interface SpotAllocationStrategy {
    Optional<Spot> allocate(Vehicle vehicle, List<Level> levels);
}

final class NearestFirstStrategy implements SpotAllocationStrategy {
    public Optional<Spot> allocate(Vehicle vehicle, List<Level> levels) {
        for (Level level : levels)                       // ordered nearest-to-entrance first
            for (Spot spot : level.spotsFitting(vehicle)) // pre-filtered by fits()
                if (spot.tryOccupy()) return Optional.of(spot);   // CAS resolves the race
        return Optional.empty();
    }
}

interface PricingStrategy { BigDecimal priceFor(Ticket ticket, Instant exitTime); }
```

```java
final class ParkingLotService {
    private final List<Level> levels;
    private final SpotAllocationStrategy allocation;
    private final PricingStrategy pricing;
    private final Map<String, Ticket> openTickets = new ConcurrentHashMap<>();

    Ticket park(Vehicle vehicle) {
        Spot spot = allocation.allocate(vehicle, levels)
            .orElseThrow(() -> new NoSpotAvailableException(vehicle));
        Ticket ticket = new Ticket(UUID.randomUUID(), spot, vehicle, Instant.now());
        openTickets.put(vehicle.plate(), ticket);          // one plate = one open ticket
        return ticket;
    }

    Receipt unpark(String plate) {
        Ticket ticket = openTickets.remove(plate);
        ticket.spot().release();
        return new Receipt(ticket, pricing.priceFor(ticket, Instant.now()));
    }
}
```

**State machine — `Spot`:**

| From | Event | To | Guard |
|---|---|---|---|
| `AVAILABLE` | `tryOccupy()` | `OCCUPIED` | CAS succeeds only if still `AVAILABLE` |
| `OCCUPIED` | `release()` | `AVAILABLE` | Called exactly once per ticket, from `unpark` |

**Concurrency:** the shared mutable state is each `Spot`'s `state` field and the free-spot pool
implied by iterating `levels`. The guard is `AtomicReference.compareAndSet`, not a `synchronized`
block around the whole allocation loop — a lock would serialise *all* gates on *all* levels for the
duration of a scan; CAS lets two gates racing for two different spots both succeed without contention,
and only the actual last-spot race resolves via one loser retrying to the next candidate. The race
without it: gate A reads `spot.state == AVAILABLE`, gate B reads the same, both set `OCCUPIED`, two
tickets point at one physical spot.

**Extension test:**
- *EV charging spots with a per-vehicle charging fee:* new `SpotType.EV`, new `fits()` branch, a
  decorator or a second `PricingStrategy` that adds a charging surcharge — zero changes to
  `ParkingLotService`.
- *Reserved/pre-paid spots:* add a `RESERVED` state and a `reserve(Vehicle, Duration)` method; the
  allocation strategy must skip `RESERVED` spots not held by the arriving vehicle. This is the first
  requirement that would force touching the state machine, which is exactly why it's the harder one to
  name unprompted.

**Traps:**
- **Trap:** a `switch (vehicle.type())` inside `ParkingLotService.park` instead of pushing
  compatibility into `Spot.fits()` — the moment a new vehicle type appears, every call site with that
  switch needs a new case. See `24-design-patterns-architecture.md` §4.1 on strategy vs a switch ladder.
- **Trap:** modelling price as a raw `double`. Use `BigDecimal` or integer cents — see
  `03-java-core.md` on `BigDecimal` for money and float rounding.
- **Trap:** a god `ParkingLot` class that does allocation, pricing, and ticket bookkeeping in one
  600-line file. Three collaborators, three invariants, three test suites.
- **Trap:** ignoring concurrency until asked. State the shared-mutable-state sentence in slot 8
  unprompted — it is the single detail that separates L4 from L5 on this exact prompt.

Cross-refs: `24-design-patterns-architecture.md` (strategy, SOLID), `05-multithreading-concurrency.md`
(CAS, `AtomicReference`), `03-java-core.md` (`BigDecimal`).

---

## 5. Design — elevator bank

**Prompt:** design the control system for a bank of elevators serving a building.

**Clarifications to ask (and the answer to assume):**
- How many cars, how many floors? *Assume 4 cars, 20 floors.*
- Scheduling goal — minimise wait time, or a simple rule? *Assume direction-aware SCAN, extensible to
  a pluggable strategy.*
- External call (hall button, direction only) vs internal call (car button, specific floor) — same
  API? *Assume both, modelled as two distinct request types.*
- Capacity/weight limits? *Out of scope for v1; name it as an extension.*
- Failure — a car goes out of service mid-ride? *Assume its pending requests are redistributed to
  other cars; name this as slot 10, don't build it.*

**The fork:** the scheduling *algorithm* (which car answers which call) must be a swappable strategy
object completely separate from each car's own state machine (which only knows how to move toward its
current target); conflating the two produces a class that both plans the whole fleet and drives one
motor, which cannot be tested or replaced independently.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `ElevatorController` | Owns all cars, receives hall calls, delegates to strategy | Exactly one car is assigned per hall call at a time |
| `Elevator` (car) | Owns its own motion state machine and door state | Never reverses direction mid-SCAN unless its request queue in that direction is empty |
| `SchedulingStrategy` (interface) | Given a call and all cars, picks a car | — |
| `HallCall` (record) | floor + direction requested from a hallway | Immutable once created |
| `CarCall` (record) | floor requested from inside a car | Immutable once created |
| `Direction` (enum) | `UP, DOWN, IDLE` | — |
| Rejected: one `Elevator` class owning fleet-wide scheduling | Couples one car's motion to every other car's state; untestable in isolation |

**Java 21 code:**

```java
enum Direction { UP, DOWN, IDLE }
record HallCall(int floor, Direction direction) {}

final class Elevator {
    enum DoorState { OPEN, CLOSED }
    private int currentFloor;
    private Direction direction = Direction.IDLE;
    private DoorState door = DoorState.CLOSED;
    private final NavigableSet<Integer> upStops = new TreeSet<>();
    private final NavigableSet<Integer> downStops = new TreeSet<>(Comparator.reverseOrder());

    void addStop(int floor) {
        if (floor > currentFloor) upStops.add(floor);
        else if (floor < currentFloor) downStops.add(floor);
    }

    void step() {                                   // one control-loop tick
        var stops = direction == Direction.DOWN ? downStops : upStops;
        if (stops.isEmpty()) { direction = flipOrIdle(); return; }
        int next = stops.first();
        currentFloor += Integer.signum(next - currentFloor);
        if (currentFloor == next) { stops.pollFirst(); door = DoorState.OPEN; }
    }
    private Direction flipOrIdle() {
        return !downStops.isEmpty() ? Direction.DOWN
             : !upStops.isEmpty()   ? Direction.UP : Direction.IDLE;
    }
}
```

```java
interface SchedulingStrategy { Elevator assign(HallCall call, List<Elevator> cars); }

final class NearestCarInDirectionStrategy implements SchedulingStrategy {
    public Elevator assign(HallCall call, List<Elevator> cars) {
        return cars.stream()
            .filter(car -> car.canServe(call))       // idle, or already moving toward call.floor()
            .min(Comparator.comparingInt(car -> car.distanceTo(call.floor())))
            .orElseGet(() -> cars.stream().min(Comparator.comparingInt(Elevator::pendingLoad)).orElseThrow());
    }
}
```

**State machine — per car direction (SCAN):**

| From | Event | To | Guard |
|---|---|---|---|
| `IDLE` | new call assigned | `UP` or `DOWN` | Direction toward the call's floor |
| `UP` | `upStops` empty | `DOWN` if `downStops` non-empty, else `IDLE` | Never reverses while `upStops` still has entries above current floor |
| `DOWN` | `downStops` empty | `UP` if `upStops` non-empty, else `IDLE` | Symmetric |

**Concurrency:** each `Elevator`'s stop sets are mutated by (a) the controller assigning new calls and
(b) the car's own control loop stepping. Guard: confine each car's mutable state to a single-threaded
executor (one thread per car, or one shared scheduler thread stepping all cars sequentially) so
`addStop` and `step` never interleave without synchronization — this is a **single-writer-per-car**
design, the same shape as the single-owner-per-document sequencer in `27-high-level-design.md` §13.
The race without it: the controller calls `addStop(12)` concurrently with `step()` reading
`upStops.first()`, corrupting the `TreeSet` (not thread-safe) or losing a stop.

**Extension test:**
- *Express cars that skip floors 2–10 except for calls originating there:* a `servesFloor(int)`
  predicate on `Elevator`, checked in `canServe` — no change to the strategy interface.
- *VIP priority calls that jump the queue:* a `Comparator` change inside the strategy's stop ordering,
  or a priority field on `HallCall` — the fork is whether priority is global (touches every car) or
  per-car (touches only `addStop`'s insertion logic); name which one and why.

**Traps:**
- **Trap:** one `Elevator` god class that both decides *which* car answers a call and *how* that car
  moves — untestable without spinning up the whole fleet.
- **Trap:** `direction` as a raw boolean (`goingUp`) instead of an enum with `IDLE` — the two-value
  model cannot represent "parked, no pending calls" and forces null/-1 sentinels elsewhere.
- **Trap:** reversing direction the instant a closer stop appears behind the car — that's not SCAN,
  it's thrashing; SCAN finishes the current direction's queue before reversing.
- **Trap:** ignoring the concurrency boundary between controller and car threads until asked.
- **Trap:** capacity/weight as an afterthought bolted onto `Elevator` instead of a check the strategy
  consults before assigning — put it in slot 10 explicitly if out of scope.

Cross-refs: `24-design-patterns-architecture.md` §4.2 (state vs strategy), `27-high-level-design.md`
§13 (single-owner sequencer), `02-java-collections.md` (`TreeSet`/`NavigableSet`).

---

## 6. Design — vending machine

**Prompt:** design a vending machine that accepts coins, dispenses an item, and returns change.

**Clarifications to ask (and the answer to assume):**
- Coin denominations and currency? *Assume US cents: 1, 5, 10, 25.*
- Multiple item slots with different prices and stock? *Assume yes — a small inventory of items keyed
  by slot code.*
- Refund mid-transaction? *Assume a `CANCEL` button that refunds inserted coins.*
- Exact change only, or must the machine make change from its own coin reserve? *Assume the machine
  makes change from a coin reserve, and can refuse a sale ("exact change only") if it can't.*
- Concurrency? *Assume single-user, one machine — this prompt is not about concurrency; say so and
  move on, don't invent contention that isn't there.*

**The fork:** this is a **pure state machine** problem — the entire design is a `VendingState`
lifecycle plus a change-making algorithm; a candidate who reaches for strategy/factory/observer here
is over-patterning a problem whose actual difficulty is enumerating every legal and illegal transition
(insert coin while dispensing, select an out-of-stock item, cancel with zero coins inserted).

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `VendingMachine` | Owns state, balance, inventory, coin reserve | Balance is only ever mutated through a state transition method |
| `VendingState` (sealed interface) | `Idle`, `HasMoney`, `Dispensing`, `OutOfStock` | Each state defines which events are legal |
| `Item` (record) | code, name, priceCents | Immutable |
| `CoinReserve` | Owns denomination counts, computes change | Never returns a partial/incorrect change set |
| Rejected: `Coin` as an object per physical coin | Denomination counts are sufficient; per-coin identity adds no invariant |

**Java 21 code:**

```java
enum Denomination { PENNY(1), NICKEL(5), DIME(10), QUARTER(25);
    final int cents; Denomination(int c) { cents = c; } }

record Item(String code, String name, long priceCents) {}

sealed interface VendingState permits Idle, HasMoney, Dispensing, OutOfStock {}
record Idle() implements VendingState {}
record HasMoney(long balanceCents) implements VendingState {}
record Dispensing(Item item) implements VendingState {}
record OutOfStock(Item item) implements VendingState {}
```

```java
final class VendingMachine {
    private VendingState state = new Idle();
    private final Map<String, Item> catalog;
    private final Map<String, Integer> stock;
    private final CoinReserve reserve;

    VendingState insertCoin(Denomination coin) {
        long balance = (state instanceof HasMoney hm) ? hm.balanceCents() : 0;
        return state = new HasMoney(balance + coin.cents);
    }

    VendingState select(String code) {
        if (!(state instanceof HasMoney hm)) throw new IllegalStateException("no funds");
        Item item = catalog.get(code);
        if (stock.getOrDefault(code, 0) <= 0) return state = new OutOfStock(item);
        if (hm.balanceCents() < item.priceCents()) return state;   // insufficient — stay in HasMoney
        long changeDue = hm.balanceCents() - item.priceCents();
        if (!reserve.canMakeChange(changeDue)) throw new ExactChangeOnlyException();
        stock.merge(code, -1, Integer::sum);
        reserve.dispense(changeDue);
        return state = new Dispensing(item);
    }
}
```

```java
final class CoinReserve {
    private final Map<Denomination, Integer> counts;   // largest-first ordering iterated
    boolean canMakeChange(long cents) { return greedyChange(cents) != null; }
    void dispense(long cents) { greedyChange(cents).forEach((d, n) -> counts.merge(d, -n, Integer::sum)); }

    private Map<Denomination, Integer> greedyChange(long cents) {   // fails on some coin sets — say so
        Map<Denomination, Integer> plan = new LinkedHashMap<>();
        for (Denomination d : List.of(Denomination.QUARTER, Denomination.DIME,
                                       Denomination.NICKEL, Denomination.PENNY)) {
            int available = counts.getOrDefault(d, 0);
            int use = (int) Math.min(available, cents / d.cents);
            plan.put(d, use); cents -= use * d.cents;
        }
        return cents == 0 ? plan : null;
    }
}
```

**State machine:**

| From | Event | To | Guard |
|---|---|---|---|
| `Idle` | `insertCoin` | `HasMoney` | — |
| `HasMoney` | `insertCoin` | `HasMoney` | balance accumulates |
| `HasMoney` | `select` (sufficient funds, in stock, change makeable) | `Dispensing` | decrements stock, dispenses change |
| `HasMoney` | `select` (out of stock) | `OutOfStock` | balance untouched, refundable |
| `HasMoney`/`OutOfStock` | `cancel` | `Idle` | refunds full balance |
| `Dispensing` | dispense completes | `Idle` | — |

**Concurrency:** deliberately none, per clarifications — a single physical machine has one buyer at a
time. **Trap:** inventing thread-safety work for a problem that explicitly doesn't have it; the
scoring signal here is *recognising* that this prompt's difficulty is state-machine completeness, not
concurrency, and saying so in slot 1.

**Extension test:**
- *Card payment alongside coins:* `HasMoney` generalises to carrying a `PaymentMethod`, and `select`'s
  guard changes from "balance ≥ price" to "authorised amount ≥ price" — the state machine's shape is
  unchanged, only the balance source changes, which is exactly the point of modelling state as sealed
  records rather than a raw `int` + `boolean` pile.
- *Greedy change fails for some coin sets (e.g. reserve has only dimes and a 15-cent change is due):*
  the algorithm needs to become DP-based coin change (`01-dsa-fundamentals.md`'s DP section) — name
  that this is the exact case where the greedy shortcut breaks, and it's a real production bug class
  (greedy change is only optimal for "canonical" coin systems like US currency).

**Traps:**
- **Trap:** modelling state as booleans (`hasMoney`, `isDispensing`) instead of a sealed hierarchy —
  produces states no boolean combination should allow (dispensing *and* out of stock at once) and
  every new state doubles the number of boolean combinations to guard against.
- **Trap:** money as `double`. Long cents or `BigDecimal`, always — see `03-java-core.md`.
- **Trap:** over-patterning: reaching for observer/strategy/factory on a 40-line problem whose actual
  content is the state table and the change algorithm.
- **Trap:** greedy change presented as universally correct without naming the canonical-coin-system
  caveat above.

Cross-refs: `24-design-patterns-architecture.md` §4.3 (state machines, illegal states unrepresentable),
`03-java-core.md` (`BigDecimal`, sealed types), `01-dsa-fundamentals.md` (DP coin change).

---

## 7. Design — library / inventory lending system

**Prompt:** design a library system: catalog books, check out and return copies, place holds, charge
fines for late returns.

**Clarifications to ask (and the answer to assume):**
- Is a "book" the catalog entry (title, author, ISBN) or the physical thing on a shelf? *Assume both
  — this distinction is the entire design.*
- Hold/reservation queue when all copies are out? *Assume FIFO per title.*
- Fine calculation — flat per day, capped? *Assume $0.25/day, capped at the book's replacement cost.*
- Multiple branches? *Out of scope for v1 — single branch, name multi-branch as an extension.*
- Membership limits (max 5 books out at once)? *Assume yes.*

**The fork:** a `Book` is the catalog metadata (one row, many physical copies); a `BookCopy` is one
physical, individually loanable unit with its own status and barcode. Collapsing them into one class
is the single most common wrong answer on this prompt — it makes "3 copies of one title, 2 checked
out" inexpressible without an ad-hoc counter that immediately desyncs from reality.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `Book` | Catalog metadata: title, author, ISBN | One `Book` per ISBN, independent of copy count |
| `BookCopy` | One physical unit, its own status + barcode | Never `AVAILABLE` while a `Loan` referencing it is open |
| `Member` | Borrower identity, loan count | Never exceeds `MAX_LOANS` open loans |
| `Loan` (record) | copy + member + due date, immutable once issued | Closed exactly once, producing a `Fine` if late |
| `HoldQueue` | Per-`Book` FIFO of waiting members | Notified in order when a copy of that title becomes available |
| `FineCalculator` (strategy) | Computes fine from days-late | Pluggable so policy changes don't touch `LibraryService` |
| Rejected: one `Book` class with a `copiesAvailable` counter | Counter drifts from actual copy state under concurrent checkout/return; copies must be individually addressable for holds and lost-copy handling |

**Java 21 code:**

```java
record Book(String isbn, String title, String author) {}

final class BookCopy {
    enum Status { AVAILABLE, ON_LOAN, ON_HOLD, LOST }
    private final String barcode;
    private final String isbn;
    private final AtomicReference<Status> status = new AtomicReference<>(Status.AVAILABLE);

    boolean tryReserveFor(Member member) { return status.compareAndSet(Status.AVAILABLE, Status.ON_LOAN); }
    void markReturned() { status.set(Status.AVAILABLE); }
}

record Loan(String id, BookCopy copy, Member member, LocalDate dueDate, LocalDate returnedOn) {
    boolean isLate() { return returnedOn != null && returnedOn.isAfter(dueDate); }
}
```

```java
interface FineCalculator { Money fineFor(Loan loan); }

final class LibraryService {
    private final Map<String, List<BookCopy>> copiesByIsbn;
    private final Map<String, HoldQueue> holdsByIsbn;
    private final FineCalculator fines;

    Loan checkout(Member member, String isbn) {
        if (member.openLoanCount() >= Member.MAX_LOANS) throw new LoanLimitExceededException(member);
        BookCopy copy = copiesByIsbn.get(isbn).stream()
            .filter(c -> c.tryReserveFor(member)).findFirst()
            .orElseThrow(() -> { holdsByIsbn.get(isbn).enqueue(member); return new NoCopyAvailableException(isbn); });
        return member.openLoan(copy, LocalDate.now().plusWeeks(3));
    }

    Fine returnCopy(Loan loan, LocalDate returnedOn) {
        loan.copy().markReturned();
        Fine fine = loan.isLate() ? new Fine(fines.fineFor(loan)) : Fine.NONE;
        holdsByIsbn.get(loan.copy().isbn()).notifyNext();   // FIFO — first waiting member is offered the copy
        return fine;
    }
}
```

**State machine — `BookCopy`:**

| From | Event | To | Guard |
|---|---|---|---|
| `AVAILABLE` | `checkout` | `ON_LOAN` | CAS; loses race → try next copy or enqueue hold |
| `ON_LOAN` | `returnCopy` | `AVAILABLE` | Emits a fine if late, notifies the hold queue |
| `AVAILABLE` | hold match | `ON_HOLD` | Reserved for the head-of-queue member for a grace window |
| any | `reportLost` | `LOST` | Removed from `copiesByIsbn` iteration, replacement cost billed |

**Concurrency:** the shared mutable state is the per-`BookCopy` status and the per-title hold queue.
Guard: CAS on `BookCopy.status` for checkout (same pattern as §4's `Spot`), and a lock-free queue or a
`synchronized` method on `HoldQueue` for enqueue/notify since FIFO ordering must be exact — two members
racing to place a hold must never both become "next in line." The race without a guard: two members
both read the copy as `AVAILABLE`, both mark it `ON_LOAN`, and the library's records show one physical
book lent to two people simultaneously.

**Extension test:**
- *Multi-branch with inter-branch transfer:* `BookCopy` gains a `branchId`; `LibraryService` becomes
  per-branch with a transfer request as a new state (`IN_TRANSIT`) — the fork is whether holds are
  branch-scoped or system-wide, name it explicitly.
- *E-book copies with no physical scarcity but a license-seat limit:* a second `BookCopy` subtype (or a
  sealed `LendableUnit` with `Physical`/`Digital` variants) where "available" means "under the license
  seat count" instead of "not on loan" — tests whether your `Status` model generalises or was
  physical-copy-specific.

**Traps:**
- **Trap:** `Book.copiesAvailable--` as a plain field mutation instead of individually addressable
  copies — cannot answer "which specific copy does member X have," which fines and lost-book billing
  both need.
- **Trap:** computing fines eagerly at due-date instead of at return time — a book returned one day
  late needs `returnedOn`, not `dueDate`, to compute the fine; conflating them either fines before the
  member had a chance to return it or under-fines.
- **Trap:** a hold queue that isn't strictly FIFO-guarded under concurrency — "first come, first
  served" is a stated business rule, not a suggestion.
- **Trap:** anemic `Loan` with public setters instead of an immutable record plus a `returnCopy`
  method that produces a *new* closed representation — see `24-design-patterns-architecture.md`'s
  anemic-model anti-pattern.

Cross-refs: `24-design-patterns-architecture.md` (anemic model, DDD entity-vs-value distinction),
`05-multithreading-concurrency.md` (CAS), `02-java-collections.md` (queue choice for `HoldQueue`).

---

## 8. Design — Splitwise-style expense split

**Prompt:** design a system where a group of people share expenses and the system tells each person
who owes whom.

**Clarifications to ask (and the answer to assume):**
- Split types — equal, exact amounts, percentages? *Assume all three, pluggable.*
- Rounding — an expense of $10 split 3 ways is $3.33/$3.33/$3.34, who eats the extra cent? *Assume the
  first N payers (by a deterministic order) absorb the remainder, one cent each.*
- Settlement — show pairwise debts, or simplify (A owes B who owes C → A owes C)? *Assume simplified
  net settlement, and say why: raw pairwise debts from N expenses can produce O(N) redundant edges.*
- Multi-currency? *Out of scope — single currency, name FX as an extension.*
- Groups vs ad-hoc splits between two people? *Assume both share the same underlying model.*

**The fork:** the split-type decision (`EQUAL`/`EXACT`/`PERCENT`) is a strategy object that produces a
list of `(person, owedAmount)` shares per expense — and the *settlement* question ("who actually pays
whom") is a completely separate concern: netting every pairwise balance in the group into a minimal
set of transfers, which is a graph-simplification problem, not an arithmetic one. Conflating "how is
this expense split" with "how does the group settle up" is the wrong-answer shape here.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `Expense` (record) | payer, total amount, participants, `SplitStrategy` | Sum of computed shares == total amount, exactly (rounding-safe) |
| `SplitStrategy` (interface) | `List<Share> compute(Expense)` | — |
| `Share` (record) | person, owedAmount | Never negative |
| `Ledger` | Accumulates net balance per person from all expenses | Sum of all balances across the group is always exactly zero |
| `SettlementSimplifier` | Turns the balance map into a minimal transfer list | Every produced transfer moves the receiver strictly toward zero |
| Rejected: `Debt` object per pairwise expense | Storing pairwise debts and simplifying later means you throw away exactly what you stored; net balance per person is the correct intermediate, not a graph of raw debts |

**Java 21 code:**

```java
record Share(String person, long owedCents) {}
record Expense(String payer, long totalCents, List<String> participants, SplitStrategy split) {}

interface SplitStrategy { List<Share> compute(Expense expense); }

final class EqualSplit implements SplitStrategy {
    public List<Share> compute(Expense e) {
        int n = e.participants().size();
        long base = e.totalCents() / n, remainder = e.totalCents() % n;
        List<Share> shares = new ArrayList<>();
        for (int i = 0; i < n; i++)
            shares.add(new Share(e.participants().get(i), base + (i < remainder ? 1 : 0)));
        return shares;    // first `remainder` people (deterministic order) absorb the extra cent
    }
}
```

```java
final class Ledger {
    private final Map<String, Long> netBalanceCents = new HashMap<>();   // +ve = is owed, -ve = owes

    void apply(Expense expense) {
        List<Share> shares = expense.split().compute(expense);
        for (Share s : shares) {
            netBalanceCents.merge(s.person(), -s.owedCents(), Long::sum);
            netBalanceCents.merge(expense.payer(), s.owedCents(), Long::sum);
        }
    }
    Map<String, Long> snapshot() { return Map.copyOf(netBalanceCents); }
}
```

```java
final class SettlementSimplifier {
    List<Transfer> simplify(Map<String, Long> balances) {
        PriorityQueue<Map.Entry<String, Long>> debtors  = maxHeapBy(e -> -e.getValue(), balances, v -> v < 0);
        PriorityQueue<Map.Entry<String, Long>> creditors = maxHeapBy(Map.Entry::getValue, balances, v -> v > 0);
        List<Transfer> transfers = new ArrayList<>();
        while (!debtors.isEmpty() && !creditors.isEmpty()) {
            var debtor = debtors.poll(); var creditor = creditors.poll();
            long amount = Math.min(-debtor.getValue(), creditor.getValue());
            transfers.add(new Transfer(debtor.getKey(), creditor.getKey(), amount));
            settle(debtor, creditor, amount, debtors, creditors);   // re-push remainder to the right heap
        }
        return transfers;
    }
}
```

**State machine:** none intrinsic — `Expense`s are immutable append-only events; `Ledger` is a pure
fold over them. Naming that there is *no* lifecycle here (unlike every other design in this file) is
itself a correct, scoring observation.

**Concurrency:** if expenses can be added concurrently within a group, `Ledger.apply` must be
serialised per group (a `synchronized` method, or route all writes for one group through a single
actor/queue) because `merge` on two keys is not atomic as a pair — two concurrent `apply` calls can
interleave their two `merge` calls and leave the zero-sum invariant transiently (and, without care,
permanently) violated. The simplest correct guard: one lock per `Ledger` instance, since expense
volume per group is low and contention is not the bottleneck here.

**Extension test:**
- *Partial settlement (someone pays back $20 of a $50 debt):* a `Payment` becomes a first-class event
  applied to the ledger exactly like an `Expense` with one participant — the fold model absorbs it
  without a new mechanism, which is the payoff of modelling the ledger as event-sourced from the start.
- *Multi-currency groups:* every `Expense` needs an FX rate snapshot at creation time (never recompute
  historical balances against today's rate) — name this as the seam, and that it's the same
  "immutable event, recorded at the time" principle as the payment extension above.

**Traps:**
- **Trap:** rounding shares independently per person (`total * pct / 100.0` as a `double`) instead of
  computing all shares from one integer-cents total and distributing the remainder deterministically
  — this is where $0.01 discrepancies silently break the "sums to zero" invariant.
- **Trap:** storing every pairwise debt from every expense and calling that "the ledger" — it's an
  event log, not a balance; net-per-person is the queryable state, and settlement simplification is
  the only place the graph view is needed, computed on demand.
- **Trap:** debt simplification implemented as brute-force pairwise cancellation (A owes B, B owes A,
  cancel) instead of the debtor/creditor max-heap greedy above, which is what actually minimises the
  number of transfers.
- **Trap:** `double` for money anywhere in this design — see `03-java-core.md`.

Cross-refs: `01-dsa-fundamentals.md` (heaps, greedy), `03-java-core.md` (`BigDecimal`/long cents),
`24-design-patterns-architecture.md` §4.1 (strategy).

---

## 9. Design — chess / tic-tac-toe game engine

**Prompt:** design a two-player board game engine — chess is the harder version, tic-tac-toe the
warm-up; the fork is identical, so the design below is stated for chess and the tic-tac-toe answer is
the same shape with one `Piece` type.

**Clarifications to ask (and the answer to assume):**
- Full rule set (castling, en passant, promotion, check/checkmate detection) or a simplified subset?
  *Assume core movement + capture + check detection; name castling/en-passant/promotion as extensions
  if time is short — don't silently skip them.*
- UI/rendering in scope? *Out of scope — the engine exposes board state and legal moves; a caller
  renders it.*
- Move history / undo? *Assume yes — it's nearly free if the board is modelled immutably.*
- Two human players, or is an AI opponent in scope? *Out of scope — a `Player` is just a source of
  moves; an AI is a different `Player` implementation later, not a change to the engine.*

**The fork:** each piece type's movement rule must be **polymorphic behaviour on the piece**, not a
central `MoveValidator` with a `switch` on piece type — a switch-on-type god method is *the* canonical
wrong answer to this prompt, because every new rule (check, pins, castling) becomes another case
threaded through the same method. Separately, **legality is layered on top of validity**: a move can
be "valid" for the piece (a bishop can slide there) but "illegal" for the position (it would leave the
king in check) — these are two different checks with two different scopes, and collapsing them is the
second most common wrong answer.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `Piece` (sealed interface: `Pawn, Rook, Knight, Bishop, Queen, King`) | Each variant knows its own candidate-move geometry | Never claims a move that requires knowing board occupancy of *other* pieces — that's `Board`'s job |
| `Board` (immutable) | 8×8 grid of `Optional<Piece>` + whose turn | Every `Board` instance is a complete, valid snapshot; moves produce a *new* `Board` |
| `Move` (record) | from, to, optional promotion | Immutable |
| `MoveGenerator` | For a `Board`, produces every piece's geometrically valid candidate moves | Delegates geometry to `Piece`, delegates occupancy/blocking to `Board` |
| `GameEngine` | Applies a move if legal, tracks history, detects check/checkmate | A move is only applied if it does not leave the mover's own king in check |
| Rejected: `MoveValidator` with `switch (piece.type())` | Exactly the god-method anti-pattern this prompt tests for |

**Java 21 code:**

```java
sealed interface Piece permits Piece.Pawn, Piece.Rook, Piece.Knight, Piece.Bishop, Piece.Queen, Piece.King {
    Color color();
    List<Square> candidateOffsets();     // geometry only — no board awareness

    record Rook(Color color) implements Piece {
        public List<Square> candidateOffsets() { return Square.rookRays(); }   // slides along ranks/files
    }
    record Knight(Color color) implements Piece {
        public List<Square> candidateOffsets() { return Square.knightHops(); } // fixed L-shapes, never blocked
    }
    record King(Color color) implements Piece {
        public List<Square> candidateOffsets() { return Square.kingAdjacent(); }
    }
}
```

```java
final class Board {
    private final Map<Square, Piece> occupied;
    private final Color turn;

    Board applyMove(Move move) {                          // never mutates — returns a new Board
        Map<Square, Piece> next = new HashMap<>(occupied);
        Piece moved = next.remove(move.from());
        next.put(move.to(), move.promotion().orElse(moved));
        return new Board(Map.copyOf(next), turn.opposite());
    }
    boolean isSquareAttackedBy(Square square, Color attacker) { /* scans attacker's pieces' geometry */ return false; }
}

record Move(Square from, Square to, Optional<Piece> promotion) {}
```

```java
final class GameEngine {
    private final Deque<Board> history = new ArrayDeque<>();

    boolean tryMove(Move move) {
        Board current = history.peek();
        if (!MoveGenerator.isGeometricallyValid(current, move)) return false;   // piece-level validity
        Board candidate = current.applyMove(move);
        Square kingSquare = candidate.kingSquareOf(current.turn());
        if (candidate.isSquareAttackedBy(kingSquare, current.turn().opposite())) return false; // legality
        history.push(candidate);
        return true;
    }
    void undo() { history.pop(); }   // free, because Board is immutable and history is just a stack of it
}
```

**State machine — game phase, not per-piece:**

| From | Event | To | Guard |
|---|---|---|---|
| `IN_PROGRESS` | `tryMove` succeeds, opponent has ≥1 legal move | `IN_PROGRESS` | — |
| `IN_PROGRESS` | mover's king attacked and mover has 0 legal moves | `CHECKMATE` | Evaluated by generating all legal moves for the side to move, not just checking |
| `IN_PROGRESS` | side to move has 0 legal moves, king not attacked | `STALEMATE` | Distinct from checkmate — same emptiness check, different guard |

**Concurrency:** deliberately none — a single game between two players is inherently sequential (turn
alternation *is* the concurrency control). Name this explicitly rather than inventing locks; if the
extension is "many simultaneous games on a server," each game's `GameEngine` is independently
single-threaded and the server-level concern (routing moves to the right game) belongs in
`27-high-level-design.md`, not here.

**Extension test:**
- *Castling and en passant:* these are moves whose legality depends on *history* (has the king/rook
  moved before, was the last move a two-square pawn push) — the seam is `MoveGenerator` gaining access
  to `history`, not `Piece`; a piece's own geometry never changes.
- *AI opponent:* a `Player` interface with `Move chooseMove(Board)` — a human-input adapter and a
  minimax/alpha-beta adapter both implement it; `GameEngine` never changes, which is the entire point
  of designing `Player` as a seam up front even though it's out of scope for v1.

**Traps:**
- **Trap:** `switch (piece.getType())` inside a shared `MoveValidator` — the canonical wrong answer;
  see `24-design-patterns-architecture.md` §4.7 on visitor/sealed-switch as the *replacement* for this,
  used correctly only when the operation, not the piece, is what varies (e.g. a `BoardPrinter` visiting
  every piece to render it — that's a legitimate sealed-switch use; movement rules are not).
- **Trap:** a mutable `Board` with `setPiece`/`removePiece` — makes undo, check-lookahead ("would this
  move leave me in check") and move history all require manual snapshotting instead of coming for free.
- **Trap:** conflating validity (can this piece geometrically reach this square, ignoring the rest of
  the game) with legality (is the resulting position legal) — checkmate detection is impossible to get
  right if these are one function.
- **Trap:** knight's move implemented as "geometrically valid but must also check nothing blocks it" —
  a knight is the one piece that is *never* blocked; a shared "check the path is clear" helper applied
  uniformly to all pieces is itself a bug for knights.

Cross-refs: `24-design-patterns-architecture.md` §4.7 (visitor, sealed pattern-matching switch),
`01-dsa-fundamentals.md` (graph/board traversal for attack detection), `04-modern-java.md` (sealed
interfaces, records, pattern matching).

---

## 10. Design — rate limiter as a library class

**Prompt:** design a rate limiter as a reusable in-process Java class that any method call can be
guarded with — contrast with `27-high-level-design.md` §4's distributed rate limiter, which is a
network service; this one never leaves the JVM.

**Clarifications to ask (and the answer to assume):**
- Algorithm? *Assume token bucket, matching §4's choice, but implemented with JVM primitives instead
  of a Lua script — that swap is the actual point of this prompt.*
- Per-key limits (per user, per API route) or one global limiter instance? *Assume per-key, via a
  factory/registry that hands out one bucket per key.*
- Thread-safety requirement? *Assume yes — the class must be safe under concurrent calls from a
  thread pool, which is the entire reason this is a design question and not a five-line utility.*
- Blocking vs non-blocking on rejection? *Assume non-blocking — `tryAcquire()` returns a boolean
  immediately; a blocking variant is named as an extension.*

**The fork:** where §4's distributed limiter needs a Lua script because the check-then-act race spans
*network calls* between independent processes, this in-process version has the same check-then-act
race spanning *threads in one JVM* — so the fix is a JVM concurrency primitive (a CAS loop, or a
`synchronized` block scoped to the one bucket), never a distributed-systems mechanism. Naming why the
mechanism differs while the algorithm doesn't is the actual signal this prompt is testing for.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `RateLimiter` (interface) | `boolean tryAcquire(int permits)` | — |
| `TokenBucketRateLimiter` | One bucket: capacity, refill rate, current tokens | `tokens` never exceeds `capacity`, never negative after `tryAcquire` returns `true` |
| `RateLimiterRegistry` | One bucket per key, created lazily | Never creates two buckets for the same key under concurrent first-access |
| Rejected: a single shared bucket for all keys | Defeats "per user/route" scoping entirely — this is the equivalent of forgetting sharding in §4 |

**Java 21 code:**

```java
interface RateLimiter { boolean tryAcquire(); }

final class TokenBucketRateLimiter implements RateLimiter {
    private final long capacity, refillPerNano;
    private final AtomicLong tokens;                 // scaled by a fixed-point factor to avoid float drift
    private volatile long lastRefillNanos = System.nanoTime();

    public boolean tryAcquire() {
        refill();
        return tokens.getAndUpdate(t -> t > 0 ? t - 1 : t) > 0;   // CAS loop under the hood; single decrement point
    }
    private void refill() {
        long now = System.nanoTime();
        long elapsed = now - lastRefillNanos;
        long grant = elapsed * refillPerNano;
        if (grant > 0) {
            tokens.getAndUpdate(t -> Math.min(capacity, t + grant));
            lastRefillNanos = now;                    // benign race: two threads may both refill; capped by min()
        }
    }
}
```

```java
final class RateLimiterRegistry {
    private final ConcurrentHashMap<String, RateLimiter> buckets = new ConcurrentHashMap<>();
    private final Supplier<RateLimiter> factory;

    RateLimiter forKey(String key) {
        return buckets.computeIfAbsent(key, k -> factory.get());   // atomic — no double-create race
    }
}
```

**State machine:** none — a token bucket is continuous state (a number), not a discrete lifecycle; say
so rather than forcing a state table where none exists, the same honest call as §8's ledger.

**Concurrency — this is the entire design:**

| Shared state | Guard | Race without it |
|---|---|---|
| `tokens` (per bucket) | `AtomicLong.getAndUpdate` — a CAS retry loop, not a lock | Two threads both read `tokens == 1`, both decrement, both succeed: over-admission by exactly the same check-then-act bug as §4 |
| `lastRefillNanos` | `volatile`, tolerating a benign double-refill race capped by `Math.min` | Without `volatile`, another thread may never observe an updated refill time (stale-read, not corruption — still a correctness bug under `05-multithreading-concurrency.md`'s memory-model rules) |
| bucket-per-key creation | `ConcurrentHashMap.computeIfAbsent` | Two threads on a cold key both see "absent," both construct a bucket — the second overwrites the first, silently resetting anyone who already acquired against the first instance |

**Trap:** using `synchronized` around the whole `tryAcquire` method "to be safe." It works, but at
high call rates from many threads it serialises every caller through one lock for what is fundamentally
a single-word update — the CAS loop is both correct and allows lock-free progress; reach for
`synchronized` only when more than one field must change atomically together (as in the bucket-map's
compound check-and-create, which is why that one *does* use `computeIfAbsent` — an atomic compound
operation, not a manual lock).

**Extension test:**
- *A blocking `acquire()` that waits for the next token instead of failing fast:* compute the wait time
  from `capacity`/`refillPerNano` arithmetic and `Thread.sleep`/`park` for it — no change to
  `tryAcquire`'s logic, a new method layered on top.
- *Promote this to the distributed limiter of `27-high-level-design.md` §4 when a second JVM
  instance appears:* the algorithm (token bucket, lazy refill) survives unchanged; only the storage and
  atomicity mechanism move from `AtomicLong` to Redis + Lua. Naming that the *algorithm* is reusable
  across both designs and only the *mechanism* changes is the strongest possible answer to "how would
  this change at scale."

**Traps:**
- **Trap:** claiming `AtomicLong` alone makes the whole class thread-safe when a second field
  (`lastRefillNanos`) participates in the same logical operation — check every field that must be
  read-then-written together, not just the one that happens to be an `Atomic*`.
- **Trap:** a `HashMap` instead of `ConcurrentHashMap` for the per-key registry — corrupts under
  concurrent `computeIfAbsent`-equivalent hand-rolled logic, or simply isn't thread-safe for concurrent
  reads during a resize.
- **Trap:** re-deriving the distributed rate limiter's Lua-script fix here — the mechanism doesn't
  transfer; there is no network hop to make atomic, only a JVM heap.
- **Trap:** floating-point token counts drifting under repeated fractional refills — fixed-point
  (scaled integer) arithmetic avoids the slow accumulation of rounding error a long-running bucket
  would otherwise show.

Cross-refs: `27-high-level-design.md` §4 (the distributed twin of this exact algorithm),
`05-multithreading-concurrency.md` (CAS, `volatile`, happens-before), `02-java-collections.md`
(`ConcurrentHashMap.computeIfAbsent`).

---

## 11. Design — logging framework

**Prompt:** design a logging library: callers log at a level, messages are formatted and written to
one or more destinations, and it must not become the bottleneck of the application it's logging for.

**Clarifications to ask (and the answer to assume):**
- Levels and filtering — per-logger level, global level, or both? *Assume both: a global threshold and
  a per-logger override.*
- Destinations — console, file, network sink, more than one at once? *Assume multiple simultaneous
  appenders (console + rolling file), pluggable.*
- Synchronous or async? *Assume async by default — this is the actual design question — with a
  synchronous mode as a config option.*
- Ordering guarantee across threads? *Assume messages from different threads may interleave by arrival
  time, but a single thread's own messages must never be reordered.*
- What happens when the sink can't keep up (disk is slow, network sink is down)? *Assume a bounded
  buffer with a configurable drop-or-block policy — never unbounded memory growth.*

**The fork:** synchronous, per-call I/O (`System.out.println` dressed up) is the naive and wrong
default — it makes every log call pay disk/network latency on the caller's thread, which is exactly
backwards for a library whose entire purpose is *not* to be the bottleneck. The correct shape is a
**layered pipeline** (`Logger` → filter → formatter → async ring buffer → `Appender`), where the
producer thread only enqueues a formatted (or lazily-formattable) record and a dedicated consumer
thread does the actual I/O — the same producer/consumer shape as `14-messaging-queues.md`'s queue
model, just intra-process.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `Logger` | Caller-facing API; checks level, builds a `LogEvent`, hands off | Never blocks on I/O in synchronous-caller mode |
| `Level` (enum, ordered) | `TRACE < DEBUG < INFO < WARN < ERROR` | Ordinal comparison decides "is this enabled" |
| `LogEvent` (record) | timestamp, level, loggerName, message/args, threadName | Immutable once created |
| `Appender` (interface) | Writes a formatted event to a destination | Owns its own I/O failure handling — a slow appender must not block others |
| `Formatter` (interface) | `LogEvent → String` | Stateless, swappable independently of the appender |
| `AsyncDispatcher` | Ring buffer + single consumer thread draining to appenders | Never reorders events from the same producer thread relative to each other |
| Rejected: `Logger` calling `Appender.write` directly | Couples caller latency to I/O latency — exactly the bottleneck this design exists to avoid |

**Java 21 code:**

```java
enum Level { TRACE, DEBUG, INFO, WARN, ERROR }
record LogEvent(Instant time, Level level, String logger, String message, String threadName) {}

interface Appender { void append(String formatted); }
interface Formatter { String format(LogEvent event); }

final class Logger {
    private final String name;
    private volatile Level threshold;                 // volatile: config reload visible without a lock
    private final AsyncDispatcher dispatcher;

    void log(Level level, String message) {
        if (level.ordinal() < threshold.ordinal()) return;     // filtered before any allocation/formatting
        dispatcher.offer(new LogEvent(Instant.now(), level, name, message, Thread.currentThread().getName()));
    }
}
```

```java
final class AsyncDispatcher {
    private final BlockingQueue<LogEvent> ringBuffer;          // bounded — see the drop/block policy below
    private final List<Appender> appenders;
    private final Formatter formatter;
    private final Thread consumer;

    AsyncDispatcher(int capacity, List<Appender> appenders, Formatter formatter, OverflowPolicy policy) {
        this.ringBuffer = new ArrayBlockingQueue<>(capacity);
        this.appenders = appenders; this.formatter = formatter;
        this.consumer = Thread.ofVirtual().start(this::drainLoop);   // one dedicated consumer, in order
    }
    void offer(LogEvent event) {
        if (!ringBuffer.offer(event)) overflow.handle(event, ringBuffer);   // DROP_OLDEST, DROP_NEWEST, or BLOCK
    }
    private void drainLoop() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                LogEvent event = ringBuffer.take();
                String formatted = formatter.format(event);
                for (Appender a : appenders) a.append(formatted);   // one slow appender delays the others — see traps
            } catch (InterruptedException ignored) { break; }
        }
    }
}
```

**State machine:** none per-event — a `LogEvent` is immutable and flows through the pipeline once.
The `AsyncDispatcher` itself has a lifecycle (`RUNNING → SHUTTING_DOWN → STOPPED`) that matters for
drain-on-shutdown, worth naming even though it's not the main event's lifecycle.

**Concurrency:** the ring buffer (`BlockingQueue`) is the single synchronization point — many producer
threads calling `Logger.log` concurrently, one consumer thread draining in arrival order per the
queue's FIFO guarantee. **Per-thread ordering is preserved because each thread's own `offer` calls
happen sequentially on that thread** (program order) and the queue preserves insertion order for a
single producer; cross-thread interleaving order is whatever arrival order the queue observed, which
matches the stated requirement exactly. The race avoided: without a queue (e.g. each thread appending
directly with a lock per appender), lock contention on hot paths turns logging into the actual
bottleneck, which is the opposite of `synchronized`-around-everything being "safe."

**Extension test:**
- *Structured/JSON logging with MDC (request-scoped context fields):* `LogEvent` gains a
  `Map<String,String> context`, populated from a `ThreadLocal` snapshotted at `log()` call time (not
  at drain time — the consumer thread has no access to the producer's `ThreadLocal`, which is exactly
  why the snapshot must happen on the producer thread before enqueue).
- *Log level changed at runtime via a config endpoint, no restart:* already free — `threshold` is
  `volatile` and re-read on every `log()` call; naming *why* it's already free (rather than adding new
  machinery) is the stronger answer.

**Traps:**
- **Trap:** synchronous per-call I/O as the default design — the single biggest wrong answer to this
  prompt; a logging library that adds disk-write latency to every request path is a production incident
  waiting to happen (see `20-observability-operations.md` on logging-induced latency).
- **Trap:** an unbounded queue "so we never drop a log line" — turns a slow appender (a stalled network
  sink) into unbounded heap growth and an eventual OOM; a bounded buffer with an explicit, named
  overflow policy is the correct trade-off, and the interviewer wants to hear you name the trade-off
  (lose some logs vs. block the app vs. OOM).
- **Trap:** one slow appender blocking all appenders because they're invoked serially on the single
  consumer thread (as drafted above) — the honest extension is per-appender queues/threads, or at
  minimum a timeout per appender; name this as a known limitation rather than let the code imply it's
  solved.
- **Trap:** capturing `Thread.currentThread().getName()` or `ThreadLocal` context on the *consumer*
  thread instead of the producer thread — silently attributes every log line to the consumer thread's
  identity.
- **Trap:** formatting the message eagerly on the hot path even when the level is disabled (string
  concatenation before the level check) — check the level first, exactly as drafted, or the "cheap
  filtering" claim is false.

Cross-refs: `14-messaging-queues.md` (producer/consumer, bounded queues, backpressure),
`05-multithreading-concurrency.md` (`BlockingQueue`, `ThreadLocal`, virtual threads, happens-before),
`20-observability-operations.md` (structured logging, why logging must not be on the request's
critical path).

---

## 12. Design — cache library with pluggable eviction

**Prompt:** design an in-process, generic cache library with a size bound and a pluggable eviction
policy (LRU to start).

**Clarifications to ask (and the answer to assume):**
- Eviction policies beyond LRU — LFU, FIFO? *Assume the interface must support swapping in any of
  them without touching the cache's core `get`/`put`.*
- TTL in addition to size bound, or size-only? *Assume both, and that they're independent concerns —
  an entry can be evicted for being stale even if the cache isn't full.*
- Thread-safety? *Assume yes — concurrent `get`/`put` from multiple threads.*
- Generic key/value types? *Assume yes — `Cache<K, V>`, no raw types.*
- Loading semantics — does a miss call a loader function automatically (cache-aside built in), or is
  it purely get/put? *Assume an optional `Function<K, V> loader` for `getOrLoad`, on top of raw
  get/put — mirrors `15-caching.md`'s cache-aside pattern, but as a library feature, not an
  architecture choice.*

**The fork:** eviction policy must be an interface the cache delegates to on every access, not a
hardcoded LRU baked into `Cache` — because the actual difficulty of this prompt is the **O(1)
access-order tracking** underneath LRU (a `LinkedHashMap` in access-order mode, or a hand-rolled
intrusive doubly linked list plus a hash map for O(1) node lookup), and that mechanism must be
swappable for LFU's frequency-count structure without rewriting `get`/`put`.

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `Cache<K, V>` (interface) | `get`, `put`, `getOrLoad`, `size` | — |
| `BoundedCache<K, V>` | Holds entries + delegates eviction decisions to a policy | Never exceeds `maxSize` entries after any `put` returns |
| `EvictionPolicy<K>` (interface) | `onAccess(key)`, `onInsert(key)`, `Optional<K> evictionCandidate()` | Decides *which* key to evict; never touches values |
| `LruPolicy<K>` | Intrusive doubly linked list + map for O(1) move-to-front | Most-recently-used key is always the list head |
| `TtlWrapper<V>` | value + expiry timestamp | Checked lazily on read, swept periodically |
| Rejected: baking LRU logic directly into `BoundedCache` | Cannot swap to LFU without rewriting the class; the whole point of "pluggable eviction" is violated |

**Java 21 code:**

```java
interface EvictionPolicy<K> {
    void onAccess(K key);
    void onInsert(K key);
    Optional<K> evictionCandidate();
}

final class LruPolicy<K> implements EvictionPolicy<K> {
    // access-order LinkedHashMap doubles as an intrusive list: iteration order == LRU order
    private final LinkedHashMap<K, Boolean> order = new LinkedHashMap<>(16, 0.75f, true);
    public synchronized void onAccess(K key) { order.get(key); }         // access-order side effect
    public synchronized void onInsert(K key) { order.put(key, Boolean.TRUE); }
    public synchronized Optional<K> evictionCandidate() {
        return order.keySet().stream().findFirst();                     // iteration order: least-recent first
    }
}
```

```java
final class BoundedCache<K, V> implements Cache<K, V> {
    private final ConcurrentHashMap<K, TtlWrapper<V>> store = new ConcurrentHashMap<>();
    private final EvictionPolicy<K> policy;
    private final int maxSize;

    public Optional<V> get(K key) {
        TtlWrapper<V> wrapper = store.get(key);
        if (wrapper == null || wrapper.isExpired()) { store.remove(key); return Optional.empty(); }
        policy.onAccess(key);
        return Optional.of(wrapper.value());
    }

    public void put(K key, V value, Duration ttl) {
        store.compute(key, (k, old) -> {
            if (old == null && store.size() >= maxSize) evictOne();
            policy.onInsert(key);
            return new TtlWrapper<>(value, Instant.now().plus(ttl));
        });
    }
    private void evictOne() { policy.evictionCandidate().ifPresent(store::remove); }
}
```

**State machine:** none for a cache entry beyond `PRESENT → EXPIRED/EVICTED`, both terminal and both
just "absent" from the caller's point of view — worth stating explicitly rather than over-modelling.

**Concurrency:** `ConcurrentHashMap` guards the key/value store's structural changes, but the eviction
**policy's own internal state (the `LinkedHashMap` order) is a second, independent piece of shared
state** that a `ConcurrentHashMap` does nothing to protect — hence the `synchronized` methods on
`LruPolicy` above. **Trap-shaped detail:** even with both individually thread-safe, `get`'s three steps
(read store, check expiry, call `onAccess`) are not atomic as a group — a concurrent eviction between
the read and the `onAccess` call can record an access for a key that's already gone. For a
correctness-critical cache (not just a best-effort speedup), the fix is a single lock (or a
`ConcurrentHashMap.compute` that does the read-check-record atomically inside one lambda) covering the
whole operation, trading some throughput for correctness — name the trade-off rather than silently
picking one.

**Extension test:**
- *LFU instead of LRU:* a new `LfuPolicy` implementing the same `EvictionPolicy<K>` interface, using a
  frequency count plus a min-heap or a bucket list for O(1) "find minimum frequency" — zero changes to
  `BoundedCache`, which is the entire payoff of the interface seam named up front.
- *Write-through to a backing store (mirrors `15-caching.md`'s write-through pattern):* `put` becomes
  `put` + a synchronous write to the loader's inverse (a `writer` function) before acknowledging —
  tests whether `Cache<K,V>`'s interface was designed generically enough to add this without breaking
  existing callers.

**Traps:**
- **Trap:** using `LinkedHashMap`'s access-order mode directly as the cache itself instead of behind an
  `EvictionPolicy` interface — works for LRU, forecloses LFU/FIFO without a rewrite, and is exactly
  the "hardcoded policy" wrong answer.
- **Trap:** treating `ConcurrentHashMap` as sufficient thread-safety for the whole cache when the
  eviction policy's bookkeeping is separate mutable state — see the concurrency section above.
- **Trap:** checking TTL expiry only via a background sweep and never lazily on read — a key that
  expired 10 minutes ago but hasn't been swept yet is returned as a stale hit; do both (lazy check on
  `get`, periodic sweep to reclaim memory for keys nobody reads again).
- **Trap:** generic type erasure surprises — `new EvictionPolicy<K>[10]` doesn't compile; don't reach
  for arrays of a generic type (see `03-java-core.md` on erasure).

Cross-refs: `02-java-collections.md` (`LinkedHashMap` access-order mode, `ConcurrentHashMap.compute`),
`15-caching.md` (eviction policies, TTL, write-through/write-behind as architecture vs library
mechanism), `03-java-core.md` (generics/erasure).

---

## 13. Design — in-memory key-value store with transactions

**Prompt:** design an in-memory key-value store supporting nested transactions (`begin`, `commit`,
`rollback`) on top of plain `get`/`set`/`delete`.

**Clarifications to ask (and the answer to assume):**
- Nesting — can a transaction begin inside another? *Assume yes, arbitrary depth, and `commit`/
  `rollback` always act on the innermost open transaction.*
- Isolation between concurrent callers, or single-threaded? *Assume single-threaded semantics for the
  core problem (this is what makes it tractable in 45 minutes); name multi-threaded isolation as an
  explicit extension, don't build it.*
- What does `get` return for a key modified in an open transaction — the transaction's view, or the
  committed value? *Assume the transaction's own uncommitted writes are visible to reads within that
  same transaction (read-your-writes), but invisible outside it until commit.*
- Delete semantics inside a transaction that's then rolled back? *Assume the delete is undone along
  with everything else — treat delete as a write, not a special case.*

**The fork:** nested transactions are implemented as an **undo journal per transaction level**, not as
copy-on-write snapshots of the whole store — snapshotting the entire map on every `begin` is O(store
size) per transaction and wasteful when a transaction touches three keys out of a million; an undo
log only records what actually changed, so `rollback` is O(keys touched), and `commit` is O(1) (just
discard the log, the changes are already live in the store).

**Class model:**

| Class | Responsibility | Invariant it owns |
|---|---|---|
| `TransactionalStore<K, V>` | Public `get`/`set`/`delete`/`begin`/`commit`/`rollback` | The live map always reflects every committed write plus every write in currently-open transactions |
| `UndoLog<K, V>` | One per open transaction: records the *prior* value (or absence) for each key first touched in this level | Records at most one undo entry per key per transaction level — first-touch wins |
| `Operation` (sealed: `Put`, `Delete`) | What kind of prior state to restore | — |
| Rejected: `Map<K,V>` snapshot per `begin` | O(n) copy per transaction regardless of how few keys it touches; also complicates read-your-writes across nesting levels since each snapshot diverges independently |

**Java 21 code:**

```java
sealed interface PriorState<V> permits PriorState.HadValue, PriorState.Absent {
    record HadValue<V>(V value) implements PriorState<V> {}
    record Absent<V>() implements PriorState<V> {}
}

final class UndoLog<K, V> {
    private final Map<K, PriorState<V>> firstTouch = new LinkedHashMap<>();   // insertion order = undo order

    void recordIfFirstTouch(K key, PriorState<V> priorState) {
        firstTouch.putIfAbsent(key, priorState);        // only the FIRST change in this level is undoable
    }
    void undoOnto(Map<K, V> store) {
        for (var entry : firstTouch.entrySet()) {
            switch (entry.getValue()) {
                case PriorState.HadValue<V> hv -> store.put(entry.getKey(), hv.value());
                case PriorState.Absent<V> a    -> store.remove(entry.getKey());
            }
        }
    }
}
```

```java
final class TransactionalStore<K, V> {
    private final Map<K, V> live = new HashMap<>();
    private final Deque<UndoLog<K, V>> txStack = new ArrayDeque<>();

    Optional<V> get(K key) { return Optional.ofNullable(live.get(key)); }   // read-your-writes: live IS current view

    void set(K key, V value) {
        recordPriorState(key);
        live.put(key, value);
    }
    void delete(K key) { recordPriorState(key); live.remove(key); }

    private void recordPriorState(K key) {
        if (txStack.isEmpty()) return;                                     // no open tx: nothing to undo
        PriorState<V> prior = live.containsKey(key)
            ? new PriorState.HadValue<>(live.get(key)) : new PriorState.Absent<>();
        txStack.peek().recordIfFirstTouch(key, prior);
    }

    void begin() { txStack.push(new UndoLog<>()); }
    void commit() { requireOpenTx(); txStack.pop(); }                      // O(1): changes are already live
    void rollback() { requireOpenTx(); txStack.pop().undoOnto(live); }     // O(keys touched this level)
    private void requireOpenTx() { if (txStack.isEmpty()) throw new NoOpenTransactionException(); }
}
```

**State machine — per transaction level:**

| From | Event | To | Guard |
|---|---|---|---|
| — | `begin()` | `OPEN` (pushed onto `txStack`) | Nesting is just another push; no special-casing depth |
| `OPEN` (innermost) | `commit()` | popped, changes retained in `live` | If this was the outermost level, the writes are now permanently committed |
| `OPEN` (innermost) | `rollback()` | popped, changes undone via `UndoLog.undoOnto` | Only this level's first-touch priors are restored — a key touched again in an *outer* level still has its own undo entry there |
| any | `commit`/`rollback` with `txStack` empty | throws `NoOpenTransactionException` | — |

**Concurrency:** none in the base design, by the stated clarification — `txStack` and `live` are
single-threaded state, and that's the honest, correct scope for this exact prompt (multi-level nested
transactions plus multi-threaded isolation in one 45-minute round is two hard problems, not one).
**Extension, named rather than built:** true multi-threaded isolation would require either (a) one
`TransactionalStore` instance per thread with a separate commit-merge protocol (optimistic, checking
for conflicting keys at commit — the same shape as `09-sql-databases.md`'s MVCC), or (b) per-key locks
held for the duration of a transaction (pessimistic, risking deadlock across transactions holding
multiple keys) — say which one you'd pick and why (optimistic if conflicts are rare, pessimistic if
transactions are long and conflict-prone) rather than building either under time pressure.

**Extension test:**
- *Iteration (`keys()`/`entries()`) while a transaction is open:* must reflect `live`'s current state
  including uncommitted writes (consistent with read-your-writes for `get`) — the seam is that
  iteration is just another read of `live`, no special-casing needed, which is the payoff of *not*
  having used separate per-level maps.
- *Savepoints (`rollback to a named point`, not just "rollback the innermost level"):* generalises
  `txStack` from a stack of single levels to allowing `rollback(name)` to pop and undo everything down
  to and including a named level — tests whether the undo-log-per-level design generalises past strict
  LIFO nesting, and it does: pop-and-undo N levels is just calling the existing `rollback()` N times.

**Traps:**
- **Trap:** snapshotting the whole map on `begin()` — correct but wasteful, and it's the wrong answer
  to "why is this an undo log and not a copy," which is the question this prompt is built to ask.
- **Trap:** recording *every* write to the undo log instead of only the *first* write per key per
  level — without `putIfAbsent`'s first-touch-wins semantics, three writes to the same key in one
  transaction would restore the value from the *second* write, not the value from before the
  transaction started.
- **Trap:** `commit()` doing anything other than popping the log — a common wrong instinct is to
  "apply" the transaction's changes on commit, which implies they weren't live before, breaking
  read-your-writes for anything that read the key mid-transaction.
- **Trap:** forgetting that a value can transition from "present" to "absent" via `delete`, and that
  the *prior state* to restore on rollback must capture "was absent" as its own case (not `null`,
  which is ambiguous with "the prior value was literally `null`" for a `Map<K,V>` that permits null
  values) — the `PriorState` sealed type above exists specifically to make that ambiguity
  unrepresentable.

Cross-refs: `09-sql-databases.md` (MVCC, optimistic vs pessimistic concurrency, isolation levels — the
distributed/durable analogue of this exact problem), `02-java-collections.md` (`Deque` as a stack,
`LinkedHashMap` insertion order), `04-modern-java.md` (sealed interfaces, pattern-matching switch).

---

## 14. More prompts, with only the fork named

Drill these the same way — paper first, 45 minutes, then check against the fork below.

| Prompt | The fork, and the trap |
|---|---|
| **ATM** | Card/PIN validation is a separate collaborator from cash dispensing; cash dispensing is itself a change-making problem identical to §6's vending machine. Trap: modelling account balance mutation and physical cash-count mutation as one operation — a dispense can fail (out of $20s) *after* the balance is already debited unless the two are ordered debit-then-dispense-then-compensate-on-failure. |
| **Ride-hailing matcher (single process)** | Nearest-driver lookup needs a spatial index (a simplified grid, not full geohash — that's `27-high-level-design.md` §8's distributed version); the fork here is the same CAS-based offer state machine as §4's parking spot, applied to a driver instead of a spot. Trap: linear-scanning all drivers per match request instead of any spatial partitioning at all. |
| **Food-order state tracking** | A single `Order` status enum (`PLACED → CONFIRMED → PREPARING → OUT_FOR_DELIVERY → DELIVERED`, plus `CANCELLED` from any pre-preparing state) with an explicit legal-transition table, exactly `24-design-patterns-architecture.md`'s "illegal states unrepresentable" principle. Trap: a `cancel()` method that doesn't check the *current* state before flipping the flag — cancelling a `DELIVERED` order must be rejected, not silently allowed. |
| **Hotel booking** | Same shape as §12's seat/room contention: a room-night is the unit of inventory, and double-booking is prevented the same way `27-high-level-design.md` §12 prevents double-booking a seat — one conditional update, checked row count. Trap: modelling availability per room instead of per room-night, which can't express "available May 1–3, booked May 4." |
| **Snake and ladder** | The board is a fixed array of special-square rules (snake head → tail, ladder bottom → top); model each special square as a `Function<Integer,Integer>` or a `Map<Integer,Integer>` lookup applied after the dice move, not an `if/else` chain checked per square. Trap: turn order and win detection as ad-hoc loop variables instead of an explicit `Game` state machine with a `Player` queue. |
| **Deck of cards / blackjack** | `Card` and `Deck` are reusable across any card game (shuffle, deal); game-specific rules (blackjack's hit/stand/bust, ace as 1-or-11) belong in a separate `BlackjackHand` that *uses* `Deck`, never in `Card` itself. Trap: hardcoding blackjack scoring into `Card`, making the deck unusable for any other card game — a clean layering test. |
| **File system tree** | Composite pattern: `FileSystemNode` (sealed: `File`, `Directory`) where `Directory` holds children and delegates `size()`/`search()` recursively — identical shape to `24-design-patterns-architecture.md` §3.3's composite. Trap: a shared interface with leaf-only operations (`addChild` callable on a `File`) — that's the composite anti-pattern named in 24. |
| **Spreadsheet with formula recalculation** | Each cell is a node in a dependency graph; a formula cell's value is derived, not stored, and changing one cell must recompute exactly its transitive dependents via topological order — reaching for a full-grid re-evaluation on every edit is the naive/wrong answer. Trap: not detecting a circular reference (`A1=B1`, `B1=A1`), which must be caught before recomputation, not discovered as infinite recursion. |
| **Notification dispatcher (in-process, not the distributed `27-high-level-design.md` §5 service)** | Observer pattern: a `NotificationCenter` with per-event-type listener lists; the fork is whether dispatch is synchronous on the caller's thread (simple, but a slow listener blocks the publisher) or handed to an executor (async, but then delivery order across listeners is no longer guaranteed) — name which you chose and why. Trap: an observer implementation that lets one listener's exception prevent every other listener from running. |
| **Meeting-room scheduler** | Interval-overlap detection per room — sort each room's bookings by start time and binary-search/scan for a conflict, or hold each room's bookings in a `TreeMap<LocalDateTime, Booking>` for O(log n) conflict checks. Trap: O(n) linear scan against every existing booking on every new request when the room has thousands of bookings; also, an off-by-one on "does 2–3pm conflict with 3–4pm" (it does not — half-open intervals). |
| **URL-shortener object model (the LLD twin of `22-system-design.md`'s system-level version)** | Base-62 encoding of an auto-incrementing ID vs a random-token generator with a collision check — the LLD version of this prompt is purely the encoding algorithm and the in-memory bidirectional map, with no sharding/replication concerns at all; don't accidentally re-derive `22`'s distributed-ID-generation section here. Trap: treating this as a system-design prompt and spending all 45 minutes on QPS estimation instead of the actual ask — the encoding function and its collision behaviour. |
| **Undo/redo text editor** | Command pattern: every edit is a reified `Command` object with `execute()`/`undo()`, held on an undo stack; redo is a second stack that's cleared the instant a *new* (non-redo) command executes — the classic bug is forgetting to clear the redo stack, letting redo replay a command whose preconditions no longer hold. Trap: storing raw text snapshots per edit instead of commands — correct but O(document size) per keystroke instead of O(1) per edit. |

---

## 15. L5 vs L6 on the same drill

Same prompt (the parking lot from §4), different bar. LLD rounds skew L4/L5; L6 signal here is rarer
but real — usually surfaced as a follow-up rather than a separate round.

| Dimension | L5 (Senior IC) answer | L6 (Staff / TL) addition |
|---|---|---|
| Correctness | Compiling code, correct allocation and pricing, thread-safe on the free-spot pool | Same, plus: names the concurrency guard's cost (CAS retry storms under a stampede at a popular exit time) and what changes if that storm is real |
| Extensibility | Strategy interfaces for allocation and pricing, demonstrated with a second implementation | Frames the *module boundary*: "allocation strategy and pricing strategy could each be owned by a different team via this interface, with a contract test as the seam" |
| Scope | Solves the stated case (single garage, in-memory) completely | Negotiates scope: "if this garage chain has 200 locations, in-memory state per process stops working — here's the line where it becomes a persistence-boundary problem, and I'd hand that to `22-system-design.md`'s method, not solve it in this round" |
| Testing | Unit tests per class, an integration test for the concurrent-allocation race | Names the specific test that *proves* the concurrency claim (N threads racing for the last spot, asserting exactly one wins) rather than asserting thread-safety by inspection |
| Trade-offs | Picks CAS over a lock and can say why | States the conditions under which the choice would flip ("if allocation logic needed to check three collaborators' state atomically together, a single lock would be simpler and CAS composition would fight you") |

**Trap for experienced candidates:** talking architecture and team ownership on a design that still
double-books the last spot. In an LLD round, correctness of the class model and the code is the floor,
not a checkbox to rush past on the way to sounding senior.

---

## 16. Machine-coding round mechanics (60–90 minutes)

The extended variant of this round expects a runnable program, not a whiteboard sketch — some tests
passing is the deliverable, not a class diagram. The mechanics differ enough to warrant their own
section.

**File layout, decided in the first two minutes:**

```
src/main/java/.../model/       core entities: records, sealed types, enums
src/main/java/.../repository/  interfaces + one InMemory* implementation each
src/main/java/.../service/     orchestration: the class with the actual business methods
src/main/java/.../Main.java    a demo driver — proves the thing runs end to end
src/test/java/.../             JUnit 5, mirroring the main package structure
```

**Build order — this is the part candidates get backwards under pressure:**

1. **Interfaces first** — the repository/collaborator contracts, even before any implementation
   compiles against real logic. This is slot 5 of the template (§2), taken literally into code.
2. **In-memory repository** — a `HashMap`-backed implementation of each interface. Trivial, but it
   unblocks every service method from day one and is a stated seam for "swap to a real DB later."
3. **Happy path only** — the one scenario from the prompt's example, wired end to end, printed from
   `Main`. Seeing *something* work by the halfway mark is the single best insurance against running
   out of time with nothing demonstrable.
4. **Edge cases** — the ones named in slot 1's scope and slot 7's state machine: not-found, capacity
   exceeded, illegal state transition, duplicate. Each becomes one `@Test`, not a `Main`-method print
   statement — this is where JUnit earns its keep over manual inspection.
5. **Tests, throughout, not at the end** — write the test for a method the moment its happy path
   compiles, before moving to the next method. Writing all the code first and "adding tests after" if
   time remains is how machine-coding rounds run out the clock with zero test coverage, which is
   itself a scored criterion in most rubrics.

**What to stub, explicitly, and say out loud that you're stubbing it:**
- Persistence beyond in-memory (a comment: `// repository interface only; a JPA impl is out of scope
  for this round`).
- Anything the prompt didn't ask for but that a real system would need (auth, logging, metrics) — name
  it in slot 11, don't build it, don't ignore it silently either.
- Input validation beyond what a test exercises — validate the paths your own tests hit; don't spend
  ten minutes hardening against inputs nobody is going to type into a 90-minute demo.

**`Main` as a demo driver:** a short, linear script exercising the happy path plus one or two edge
cases end to end, with `System.out.println` at each step — this is your safety net if the interviewer
asks "show me it working" and your test suite alone (correctly) prints nothing to a terminal.

**JUnit 5 discipline under time pressure** (full mechanics in `16-testing.md`):
- One `@Test` per behaviour, named for the behaviour (`parkVehicle_whenLotFull_throws`), not
  `test1`/`test2` — a reviewer skimming test names should understand the spec without reading bodies.
- Prefer `assertThrows`/`assertEquals` over manual try/catch — faster to write and unambiguous about
  intent.
- A `@BeforeEach` building one shared fixture (a lot with 2 levels, 3 spots) beats re-constructing the
  object graph inside every test method.
- Skip parameterised tests and custom extensions under a 90-minute clock — they cost setup time this
  round doesn't have; plain repeated `@Test` methods are the correct trade-off here, unlike in
  production code.

Cross-refs: `16-testing.md` (JUnit 5 mechanics, Mockito, test pyramid), `24-design-patterns-architecture.md`
(the interfaces you're standing up in step 1 are the DIP seam that architecture is named for).

---

## 17. Self-scoring rubric

Score each 0/1/2 immediately after the timer, before re-reading the worked design. Below 14/20 means
re-drill the same prompt in a week rather than moving to the next one.

| # | Criterion | 2 points means |
|---|---|---|
| 1 | Scope cut | Named in-scope use cases *and* explicitly deferred the rest, inside 3 minutes |
| 2 | Nouns → classes | Every class maps to a real responsibility; named at least one rejected candidate class and why |
| 3 | API before implementation | Public method signatures written before any field or data structure |
| 4 | Invariant per class | Can state, for every class, the one thing that must always be true while it exists |
| 5 | The fork named | Identified the one decision the prompt is testing, unprompted, before writing code |
| 6 | Immutable core entities | Entities are records/sealed types with behaviour, not getter/setter bags |
| 7 | State machine correctness | Every legal transition covered; at least one illegal transition explicitly rejected, not silently allowed |
| 8 | Concurrency named correctly | Stated what's shared and the exact guard — or correctly stated that there is none needed, and why |
| 9 | Extension test | Named 2 plausible next requirements and where each lands, unprompted |
| 10 | Traps avoided | God class, switch-on-type, double for money, anemic model — none present in the final design |

---

## Atomic concept checklist

- [ ] This guide is one-process LLD; `22-system-design.md`/`27-high-level-design.md` are the multi-machine twin, and `24-design-patterns-architecture.md` owns the pattern mechanisms this guide only applies.
- [ ] The 11-slot LLD template: scope, actors, nouns→classes with rejections, responsibilities/invariants, API before implementation, immutable core entities, state machine, concurrency boundary, persistence boundary, extension test, what you didn't build.
- [ ] API signatures before data structures — designing the contract first prevents the implementation from shaping (and constraining) the API.
- [ ] Naming the fork — the one decision a prompt exists to test — unprompted is the highest-value sentence in the round, same principle as slot 7 in the HLD template.
- [ ] The forcing-function map: allocation strategy, per-unit state machine, pure state machine, entity-vs-copy, split-strategy + graph netting, polymorphic move rules, in-process concurrency primitive, layered async pipeline, pluggable eviction, undo-log transactions.
- [ ] **Parking lot:** allocation strategy and pricing strategy are separate collaborators from `ParkingLotService`; the free-spot pool's mutation is guarded by CAS on each `Spot`, not a lock around the whole allocation scan.
- [ ] **Elevator bank:** fleet-wide scheduling strategy is a separate object from each car's own SCAN state machine; each car's stop-set mutation is confined to a single-writer thread/executor.
- [ ] **Vending machine:** a pure state-machine problem — sealed `VendingState` records make illegal combinations unrepresentable; greedy change-making is only correct for canonical coin systems.
- [ ] **Library system:** `Book` (catalog metadata) and `BookCopy` (individually loanable unit) are two different classes with two different lifecycles; a copy-count integer on `Book` alone cannot express which specific copy a member holds.
- [ ] **Splitwise:** split strategy (how one expense divides) and settlement simplification (how the group nets out) are two independent concerns; the ledger is a net-balance-per-person fold over immutable expense events, not a stored graph of pairwise debts.
- [ ] **Chess/tic-tac-toe:** piece movement geometry is polymorphic per `Piece`, never a central switch-on-type; validity (can the piece reach the square) and legality (does the move leave your king in check) are two separate checks with two separate scopes.
- [ ] **In-process rate limiter:** same token-bucket algorithm as the distributed version in `27-high-level-design.md` §4, but the atomicity mechanism is a JVM primitive (CAS/`AtomicLong`), never a Lua script — the algorithm transfers across scales, the mechanism does not.
- [ ] **Logging framework:** a layered pipeline (`Logger` → filter → formatter → async ring buffer → `Appender`) so the caller's thread never pays I/O latency; per-producer-thread ordering is preserved by the queue, cross-thread ordering is arrival order.
- [ ] **Cache library:** eviction policy is an interface (`EvictionPolicy<K>`) the cache delegates to, so LRU can be swapped for LFU without touching `get`/`put`; the policy's own bookkeeping (e.g. `LinkedHashMap` access order) is separate shared mutable state from the value store and needs its own guard.
- [ ] **Transactional KV store:** nested transactions are an undo journal per level (first-touch-wins per key), not a copy-on-write snapshot per `begin` — `commit` is O(1), `rollback` is O(keys touched); a `PriorState` sealed type distinguishes "had a value" from "was absent" so rollback of a delete is unambiguous.
- [ ] Money is always `BigDecimal`/long-cents, never `double`, across every design in this file.
- [ ] Every entity with a lifecycle gets a legal-transition table; a design with no lifecycle (Splitwise's ledger, the rate limiter's bucket) states that explicitly rather than forcing a table where none belongs.
- [ ] Concurrency guard choice follows from what's shared and how many fields must change together: CAS/`AtomicLong`/`compareAndSet` for a single field, `ConcurrentHashMap.compute`/`computeIfAbsent` for an atomic compound map operation, a lock/`synchronized` only when multiple independent fields must move together.
- [ ] The extension test (name 2 future requirements and where they land) is scored even when not asked — it's the strongest evidence a design is open for extension rather than merely correct for the stated case.
- [ ] Machine-coding build order: interfaces → in-memory repository → happy path wired end to end → edge cases as tests → tests written alongside each method, never deferred to the end.
- [ ] Traps common across this whole file: god class, switch-on-type instead of polymorphism, anemic getter/setter entities, over-patterning a 40-line problem, ignoring concurrency until asked, singleton-as-global-mutable-state, designing persistence before behaviour.
- [ ] L6 signal on an LLD round is rarer than on HLD but real: it shows up as blast-radius/cost/module-ownership framing layered *on top of* a correct L5 design, never as a substitute for one.
- [ ] Score every drill on the 10-criterion rubric; below 14/20, re-drill the same prompt in a week before moving to the next one.
