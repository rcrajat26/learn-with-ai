## The example domain

*Hand this section verbatim to every writer, with that row's example assignment.*

**Every example comes from QuizStakes**, the shared fictional domain in
`src/scenario/scenario.md`. It is a regulated skill-based betting platform:
onboarding with status codes, compliance gates, restrictions, a bonus-and-cash
ledger, deposits and withdrawals, batched payment runs.

**Banned outright:** `Dog extends Animal`, `Foo` / `Bar` / `Baz`, `thread1` /
`thread2`, `MyClass`, `Employee`, `Shape` / `Circle` / `Square`, `Person`,
`test1`, `doSomething()`. A throwaway name in a code block is a defect, not a
style choice — re-dispatch the file.

**Where to take each thing from:**

| What you need | Where in `src/scenario/scenario.md` |
|---|---|
| A scenario for a concept | §15 Example Bank — 15.1 concurrency, 15.2 distributed/consistency, 15.3 data & storage, and the sections after |
| Vocabulary and status codes | §3 Glossary and §3.1 Status Code Index — `AA-610`, `DEP-301 CAPTURED`, `CLIENT_BONUS_RESERVED` |
| Services and their boundaries | §4 Service Catalog, §5 High-Level Architecture |
| Entities, fields, relationships | Appendix C — value types, aggregates, layering |
| Any number — volume, latency, size, lifetime | Appendix A. **Take the figure; never invent one.** |
| Money, buckets, ledger invariants | §11 Funds & Ledger Model |
| Flows worth walking end to end | §12 Client Payment Flows, §8 Onboarding Journey |
| Infrastructure or deployment naming | Appendix B |

**Rules that keep it honest:**

- Take names, status codes, and numbers **verbatim**. A reader who has met
  `CLIENT_BONUS_RESERVED` once must meet the same spelling every time.
- Reach for the Example Bank row that matches the concept before inventing a
  scenario. If §15 has no row for it, extend the domain in the same register —
  a new operation on an existing service, not a new universe.
- **Do not edit `src/scenario/scenario.md`.** It is read-only for this pipeline.
- The domain must not become the lesson. The concept stays the subject; QuizStakes
  is the material it is demonstrated on. If the example needs three paragraphs of
  domain setup before the concept appears, pick a smaller slice of the domain.
- **Where the concept is genuinely domain-free** — a language mechanic, a JVM
  constant, a bit trick — a minimal snippet with honestly-named locals is fine.
  Do not bolt a betting platform onto `Integer` caching. What is never fine is
  `Foo` and `thread1`.
- §1's reading-order table maps topic areas to the sections worth reading first.
  Use it when choosing a row's example assignment.

### Choosing examples at planning time

Example selection is **yours, not the writer's** — it is how the set stays
coherent across files that never see each other. For each sealed row, pick the
domain slice before dispatch and record it in the row's `Examples` column. Two
rows may reuse the same entity; two rows must not tell contradictory stories
about it.

---
