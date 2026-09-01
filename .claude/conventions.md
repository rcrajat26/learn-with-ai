# Conventions — Naming, Structure, Tier Tagging

## File naming

| Artifact | Path | Example |
|---|---|---|
| Daily notes | `w<N>/day<D>-notes.md` | `w2/day7-notes.md` |
| Weekly overview | `w<N>/week<N>-notes.md` | `w3/week3-notes.md` |
| Architecture-blog dissection | `architecture-notes/YYYY-MM-DD-blog-title.md` | `architecture-notes/2026-06-03-discord-cassandra.md` |
| Behavioral stories | `behavioral/stories.md` | (single file, append over weeks) |
| Progress journal (user-maintained) | `progress.md` (root) | (one running log) |

Week N covers days `5N-4` through `5N`. Always verify against the plan.

## Daily-notes structure (mandatory)

Mirror `example-day-notes.md` exactly:

```
§ 0   Day Header              (week#, day#, type, time budget, why-this-day-matters,
                               prerequisites, forward setup, prereq checklist)
§ 1   Table of Contents       (anchored to all §)
§ 2.A Theory topic 1          (15 sub-sections, see below)
§ 2.B Theory topic 2          (15 sub-sections, if applicable)
§ 3.A Problem 1               (17 sub-sections, see below)
§ 3.B Problem 2               (17 sub-sections)
§ 3.C Problem 3 (if any)
§ 4   Applied / Build / DS-D / Mock-D block  (when day type warrants)
§ 5   Behavioral / Architecture-judgment block  (when applicable)
§ 6   Cross-References        (callbacks + foreshadows + project map)
§ 7   Cheatsheet
§ 8   Self-Assessment Checklist
§ 9   Glossary
§ 10  References

Footer: line count, section count, topics covered, anything deferred,
Senior IC coverage assessment, Staff coverage assessment, target reading times.
```

## § 2 — Theory block sub-sections (15, all mandatory)

```
2.X.1   Origin & Motivation                       [BOTH]
2.X.2   Intuition                                  [BOTH]
2.X.3   Formal Definition                          [BOTH]
2.X.4   Mechanics — How It Actually Works          [BOTH]
2.X.5   Complexity / Cost Model                    [BOTH]
2.X.6   Implementation Walkthrough                 [BOTH]
2.X.7   Edge Cases & Pitfalls                      [BOTH]
2.X.8   Internals — One Layer Deeper               [STAFF]
2.X.9   Real-World Failure Case Studies            [STAFF]
2.X.10  Alternatives — When NOT to use             [BOTH + STAFF extension]
2.X.11  Connection to the Three Portfolio Projects [BOTH]
2.X.12  Connection to the Real World               [STAFF]
2.X.13  Common Misconceptions                      [BOTH]
2.X.14  Interview Framing                          [BOTH]
2.X.15  Further Reading                            [BOTH]
```

Minimums per theory topic:
- At least 1 real-world failure case study with named incident.
- At least 1 worked example with full trace.
- At least 3 alternatives discussed.

## § 3 — Problem block sub-sections (17, all mandatory)

```
3.X.1   Problem Statement                        [BOTH]
3.X.2   Clarifying Questions                     [BOTH]
3.X.3   Brute Force                              [BOTH] (ALWAYS show first)
3.X.4   Intermediate Improvements                [BOTH]
3.X.5   Optimal Solution(s)                      [BOTH]
3.X.6   Worked Trace                             [BOTH]
3.X.7   Complexity Analysis                      [BOTH]
3.X.8   Edge Cases                               [BOTH] (≥5)
3.X.9   Common Bugs                              [BOTH]
3.X.10  Pattern Recognition                      [BOTH]
3.X.11  Multi-Solution Comparison Table          [BOTH]
3.X.12  Follow-Up Questions                      [BOTH] (≥3 with drafted answers)
3.X.13  Scale-Up Addendum                        [STAFF]
3.X.14  Real-World Analogue                      [STAFF]
3.X.15  Trade-Off Drill                          [STAFF] (≥2 framed Q with 3-axis answer)
3.X.16  Junior vs Senior vs Staff Lens           [BOTH]
3.X.17  Interview Communication Script           [BOTH]
```

Minimums per problem:
- Brute force MUST appear before optimal.
- At least 5 edge cases.
- At least 2 trade-off drills with full 3-axis answers.
- At least 1 streaming or distributed variant.

## Tier tagging

Every distinct sub-block — section heading, sub-section heading, even bullet
clusters where tier diverges — must carry one tag:

- **[BOTH]** — applies to Senior IC and Staff equally. Default in doubt.
- **[SENIOR IC]** — required for L5 bar; mechanics, fluency, correctness.
- **[STAFF]** — L6 extensions; reserve for content a Senior IC could skip.

When tier diverges within a section: keep [SENIOR IC] base, add [STAFF]
extension as a separate sub-block. Never blend tiers in one prose block.

## Length & depth

- Target 1500–2000 lines per day.
- Under 1500 → under-covered; expand.
- Over 2000 → check for filler; prune narrative ("Let's now…", "It's important to note…").
- Length is not a goal; completeness is. Match what the topic warrants.

## Style

- Java 21 idiomatic. Records, var (sparingly), pattern matching, modern Spring Boot 3.x.
- ```java / ```yaml / ```sql / ```hcl fences for every code block.
- Markdown tables for any comparison ≥ 3 items.
- Second person where instructional ("you'll hit this when…").
- First-person plural sparingly for engineering culture statements.
- No emojis. No filler. No exclamation points (rare exceptions allowed).
- Inline external URLs at point of mention AND duplicate in § 10 References.

## Cross-references

- Callbacks: name the day number AND specific concept ("Day 1 § 2.B's `computeIfAbsent` idiom").
- Foreshadows: name the day number AND what gets built ("Day 67 Spring Kafka wiring builds on today's length-prefix framing").
- Project integration: name the project + day + how it lands ("Project 2 Day 54 uses this for idempotency-key dedup").

## Common pitfalls (avoid)

- Skipping brute force on problems.
- Compressing § 2.8 (Internals) when topic is "simple."
- Forgetting the streaming/distributed variant on problems.
- Writing trade-off drills without 3-axis structure.
- Vague cross-references ("we'll see this later" — name the day).
- Filler phrases at section transitions.
- Tier-tagging only at the section level (must tag sub-blocks too).