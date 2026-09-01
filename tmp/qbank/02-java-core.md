# 02 — Java Core

**What this decides:** whether you need language-fluency drills, how much of
the plan's Java side-slots you keep, and whether modern-Java (Week 15) needs
extra prerequisite time.

---

## Ladder

### Q1 [L1] explain-back — String immutability
Why are Java Strings immutable, and name two consequences.
**Strong answer:** safety (keys/security/threading), string pool interning,
hashCode caching; consequence: concatenation creates new objects (→ StringBuilder).
**Red flags:** "because Java made them final" with no why.

### Q2 [L1] explain-back — `==` vs `equals`
When do they differ, and what's the Integer trap?
**Strong answer:** `==` compares references (primitives: values); `equals`
logical equality. Trap: `Integer` cache −128..127 makes `==` "work" for small
values and fail for large — predict `Integer a=127,b=127; a==b` (true) vs
`128` (false).

### Q3 [L2] explain-back — equals/hashCode contract
State the contract and describe concretely what breaks in a `HashMap` when
you override `equals` but not `hashCode`.
**Strong answer:** equal objects MUST have equal hashCodes (reverse not
required). Broken: two logically-equal keys hash to different buckets →
`get` with an equal key misses; duplicates coexist. Bonus: consistency
requirement, why mutable fields in hashCode are dangerous (see 01/C5).

### Q4 [L2] explain-back — Generics & erasure
Why can't you write `new T[10]` or `list instanceof List<String>`? What is
erasure? What does PECS mean?
**Strong answer:** generics are compile-time only; erased to raw/bound at
runtime → no reifiable type. PECS: producer-extends (`? extends T` to read),
consumer-super (`? super T` to write); example: `Collections.copy(dest, src)`
signature.
**Red flags:** can use generics but has never heard of erasure → 0.5 max.

### Q5 [L3] predict-output — Autoboxing + collections
```java
List<Integer> list = new ArrayList<>(List.of(5, 10, 15));
list.remove(10);
System.out.println(list);
```
**Answer:** throws `IndexOutOfBoundsException` — `remove(int)` overload wins
over `remove(Object)`; it tries index 10 on a size-3 list. Fix:
`list.remove(Integer.valueOf(10))`. Full credit needs the overload-resolution
explanation.

### Q6 [L3] predict-output — ConcurrentModification
```java
List<String> l = new ArrayList<>(List.of("a", "b", "c"));
for (String s : l) if (s.equals("b")) l.remove(s);
```
**Answer:** `ConcurrentModificationException` (fail-fast modCount check in
the iterator). Fixes: `iterator.remove()`, `removeIf`, or iterate a copy.
Bonus: knows it can *sometimes* not throw (removing second-to-last element)
— that detail signals real experience.

### Q7 [L3] spot-the-bug — Streams
```java
List<String> names = users.stream()
    .filter(u -> u.getAge() > 18)
    .peek(u -> u.setVerified(true))     // (1)
    .map(User::getName)
    .toList();
long count = users.stream().filter(User::isVerified).count();  // (2)
```
What's wrong or fragile here?
**Strong answer:** (1) `peek` used for side effects — legal but fragile
(skipped under some short-circuiting; wrong tool — mutation in a pipeline);
(2) depends on (1) having run — hidden ordering coupling between two
pipelines. Also: mutating source objects inside a stream is a smell.
**Score 0.5** if only "peek is for debugging" without the coupling point.

### Q8 [L3] write-it `[OPEN-EDITOR — 15 min]` — Comparator fluency
Given `record Employee(String dept, String name, double salary)`, produce,
using streams: (a) employees sorted by dept ascending then salary descending;
(b) highest-paid employee per dept as a `Map<String, Employee>`; (c) average
salary per dept.
**Answer sketch:** (a) `Comparator.comparing(Employee::dept)
.thenComparing(Comparator.comparingDouble(Employee::salary).reversed())`;
(b) `groupingBy(dept, collectors maxBy(...))` or `toMap(dept, identity,
BinaryOperator.maxBy(...))`; (c) `groupingBy(dept, averagingDouble(salary))`.
**Score 1:** all three compile-correct without flailing. **0.5:** two of three.

### Q9 [L4] discriminator — Immutability by design
"Design a `Money` class. Walk me through your decisions."
**L1 answer:** fields + getters + setters. **L2:** final fields, no setters,
equals/hashCode. **L3:** record or final class, `BigDecimal` amount (never
double — can say why: binary floating point can't represent 0.1), currency
handling, arithmetic returns new instances. **L4:** validation in constructor,
rounding-mode policy explicit, why value objects reduce whole bug classes,
serialization/JSON mapping concerns. Score by which tier your answer matches
(L2 answer = 0.5 on this L4 question; L3+ = 1).

### Q10 [L4] discriminator — Modern Java awareness
"What changed in Java between 8 and 21 that you actually use or would use?"
**Strong answer (any 4+ with a why):** records (DTO boilerplate), sealed
interfaces + pattern-matching switch (exhaustive domain modeling), `var`
(judiciously), text blocks, `Optional` discipline, Streams `toList()`,
virtual threads (I/O-bound concurrency), switch expressions.
**Red flags:** stuck on Java 8 features only → note as a modernization gap,
which changes Week 15 prerequisites.

---

## Breadth checklist (rate 0–3)

- [CORE] Collections API fluency: `computeIfAbsent`, `getOrDefault`, `merge`
- [CORE] `Comparable` vs `Comparator`; writing comparators without looking it up
- [CORE] Exceptions: checked vs unchecked — mechanics AND your opinion on when to use which
- [CORE] `Optional` — proper use (return types) vs abuse (fields, parameters)
- [CORE] Interfaces: default methods, functional interfaces, lambdas vs method refs
- `final` semantics (variable/method/class), effectively-final in lambdas
- Nested/inner/anonymous classes; what captures what
- Enums beyond constants (fields, methods, `EnumMap`)
- `String.intern`, text blocks, `StringBuilder` vs `StringBuffer`
- Serialization (Java native) — why it's largely avoided now
- Reflection & annotations — how frameworks find your annotations at runtime
- Class loading basics (classpath, `NoClassDefFoundError` vs `ClassNotFoundException`)
- Java Memory: pass-by-value semantics for references (can you settle this classic debate correctly?)
- Records: compact constructors, when NOT to use them
- Sealed classes/interfaces — heard of? used?
- var — where it's disallowed
- BigDecimal pitfalls (`equals` vs `compareTo`, construction from double)
- Date/time API (`Instant` vs `LocalDateTime` vs `ZonedDateTime`; storing timestamps correctly)
