# Ad-hoc Paper 1 — Modern Java, JVM Internals & Pattern Recognition

**Rules:** closed book, no search. `[CODE]` questions allow a plain editor.
Answer separately before opening `ad-hoc-paper-1-key.md`. Suggested time: 80 min.
18 questions, 1 mark each.

**Why this paper exists:** it covers territory the E1–E5 / M1–M2 / M5 papers
never sampled — Java 9–21 language features, the JVM diagnostic toolkit, and
DSA pattern *recognition* (as opposed to complexity theory, which has been
measured five times). Difficulty sits at the easy→medium boundary.

## Section 1 — DSA pattern recognition

**Q1.** For each problem statement, name the pattern you would reach for and
give the resulting time complexity. One line each, no code.
(a) Longest substring with at most K distinct characters.
(b) For each element in an array, find the next element to its right that is
larger than it.
(c) Given a sorted array of 10⁷ integers, find whether any two sum to a target.
(d) Split an array into M contiguous parts, minimizing the largest part sum.

**Q2.** The problem says: `1 ≤ n ≤ 20`. Then a second version says
`1 ≤ n ≤ 10⁵`. What does each constraint tell you about the intended solution's
complexity class, and why is reading it *before* designing worth doing?

**Q3.** `[CODE — 15 min]` Write `int[] twoSum(int[] nums, int target)`
returning the indices of the two numbers that add to `target` (exactly one
solution exists, you may not use the same element twice). State the complexity
of your solution AND of the brute force you rejected.

**Q4.** Detecting a cycle in a linked list: describe the fast/slow pointer
method. Then answer the follow-up interviewers always ask — once the pointers
meet, how do you find the **first node of the cycle**?

## Section 2 — Java collections internals

**Q5.** You need an LRU cache with a fixed maximum size, in a single thread.
Which JDK class gives you this almost for free, what constructor argument turns
the behaviour on, and which method do you override? Then: name one surprising
consequence of that mode for a `get()` call.

**Q6.** Rank these three for iteration and explain the mechanism in one line
each: (a) removing elements from an `ArrayList` inside a for-each loop;
(b) `list.removeIf(...)`; (c) `Iterator.remove()`. What exactly throws in
case (a), and what internal field pair produces it?

## Section 3 — Modern Java: streams and Optional

**Q7.** Predict the output and explain:
```java
List<String> names = List.of("ann", "bob", "cal");
Stream<String> s = names.stream().peek(System.out::println).map(String::toUpperCase);
System.out.println("before terminal");
List<String> out = s.toList();
```
Then: what happens if you call `s.toList()` a second time, and what is the one
rule about `peek` you should state in an interview?

**Q8.** `Collectors.toMap(User::getEmail, Function.identity())` runs fine in
testing and throws in production. Name the two distinct things that can make it
throw, and give the fix for each.

**Q9.** `groupingBy(Order::getStatus)` — what concrete Map and List
implementations do you get by default, and how would you get a `TreeMap` of
`Set`s instead? Also: what is the difference between `stream.toList()` and
`stream.collect(Collectors.toList())`?

## Section 4 — Modern Java: language features (9–21)

**Q10.** Records. (a) Write a `record Money(String currency, BigDecimal amount)`
that rejects a null currency and a negative amount. (b) A record has a
`List<String> tags` component — in what sense is the record still mutable, and
what do you do about it?

**Q11.** Sealed interfaces plus pattern-matching switch. Show a
`sealed interface Shape permits Circle, Square` and a switch expression that
computes area. Then state the concrete engineering benefit over an
`if (x instanceof ...)` chain — what class of bug does it convert into a
compile error?

**Q12.** Virtual threads (Java 21). (a) What is the actual mechanism — what
happens to the carrier thread when a virtual thread performs a blocking socket
read? (b) Name the situation that defeats it ("pinning") and the workaround on
JDK 21. (c) Give one thing virtual threads do **not** help with, and one thing
you lose by replacing a fixed thread pool with them.

**Q13.** For each, say whether it is Java 8 or later, and what problem it
solves in one line: `var`, text blocks, switch expressions,
`Optional.orElseThrow()`, sequenced collections (`getFirst`/`getLast`).

## Section 5 — JVM memory and errors

**Q14.** Your service dies with `java.lang.OutOfMemoryError`. Name the four
distinct messages that can follow that colon, and say what each one actually
means. Then: which JVM flag should have been set beforehand so you can
investigate at all?

**Q15.** A container has `memory: 2Gi`. A colleague sets `-Xmx2g`. Explain why
this is wrong: list the memory regions the JVM consumes **outside** the heap,
name what the kernel does when the total exceeds the cgroup limit, and give the
flag you would use instead.

**Q16.** `ClassNotFoundException` vs `NoClassDefFoundError`: what triggers each,
and when you see `NoClassDefFoundError` on a class you know is on the classpath,
what earlier exception should you go looking for in the log?

## Section 6 — JVM diagnostics

**Q17.** A production JVM is pinned at 100% CPU. You have SSH access and the
JDK tools. Walk through the exact command sequence that identifies **which Java
thread** is burning the CPU — include how you bridge from the OS thread ID to
the thread dump, and say what you should rule out first.

**Q18.** A service's memory grows steadily for three days, then OOMs; restarts
fix it for another three days. (a) What single metric tells you it is a real
leak rather than normal heap churn? (b) Name the two artifacts you would
capture and the tool you would open the second one in. (c) In that tool, which
size measure identifies the culprit, and why is the other one misleading?