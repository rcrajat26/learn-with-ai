# 03 Java Core — Index and file plan

**Target version: Java 21 LTS.**

| | |
|---|---|
| Topic | 03 Java Core |
| Source prompt | `src/metadata/prompts/03-java-core-prompt.md` |
| Prompt SHA-256 | `69c8de176b95a0fcdf447ae535311a164917ec68f74c207dc15832efd59c549e` |
| Prompt last modified | 2026-08-28 23:57:55 (3096 lines) |
| Syllabus leaves | **1033** enumerated (see *Leaf count correction* below) |
| Diagrams | 139 manifest ids: **117 SVG** + **22 Markdown tables** |
| Note files | 61, plus this index |

On resume: if the prompt hash no longer matches, every row reverts to `planned` and the set is
rebuilt. Otherwise dispatch only the rows marked `planned` or `blocked`.

---

## Leaf count correction

The prompt's `# TASK` and `## Leaf coverage` sections state **933** leaves and give
`Part 1: 291`. The per-section `*(N leaves)*` markers inside Part 1 actually sum to **391**, and
the file contains **1033** lines matching the leaf-number pattern `N.N.N `. Parts 2–5 reconcile
exactly (232 / 257 / 61 / 92).

The 933 figure is therefore a one-digit slip in Part 1's subtotal, not a missing hundred leaves.

**This plan covers all 1033 enumerated leaves.** Every leaf in the prompt is assigned to exactly
one file in the ledger below. Nothing is dropped; only the headline total was wrong.

| Part | Prompt says | Enumerated | Owning files |
|---|---|---|---|
| 1 — Basics | 291 | **391** | rows 1–2, 6–10, 12, 16, 21–22, 25–26, 29, 31–32, 35, 38 |
| 2 — Intermediate | 232 | 232 | rows 13, 17–18, 33, 36, 39–44, 47, 49–51 |
| 3 — Internals | 257 | 257 | rows 3–5, 11, 14–15, 19–20, 23–24, 27–28, 30, 34, 37, 45–46, 48 |
| 4 — Build it | 61 | 61 | rows 52–56 |
| 5 — Interview & retention | 92 | 92 | row 61 |
| **Total** | **933** | **1033** | |

---

## Reading order

**First careful pass — cover to cover.** Follow the file plan in row order, 1 through 61. It is
built so that every mechanism is introduced before it is relied on: the substrate and the
class-file model first, then values and conversions, then the reference world, then the
internals of each, then the from-scratch builds, then the interview wrap-ups.

**Night before the interview.** Read only these, in this order:

1. `94-interview-questions-and-drills.md` — all 80 questions, the trap index, the numbers drill
2. `90`–`93` interview files — the five puzzles in each
3. Every file's `## Cheat sheet` section, in row order
4. `strings/03-internals-string.md`, `wrappers-and-boxing/03-internals-boxing.md`,
   `classes-and-initialization/03-internals-class-loading-and-init.md`,
   `exceptions/03-internals-exception-mechanics.md`, `generics/03-internals-erasure.md` —
   the five internals files that carry the most-asked mechanisms

---

## File plan

`Est.` is the planned line count (target 350–650; 900 is the hard split).

The original ceiling was 600. It was raised to 900 after measurement: a dense
section's verbatim body plus the mandatory tail (header, 3+ pitfalls, cheat
sheet, 5+ self-tests, open questions, footer — roughly 130–150 lines) puts a
hard floor near 670–940 on sections like §1.3 integral arithmetic, §1.6
operators and §1.8 switch. Enforcing 600 made three separate writers either
squeeze to 597–599 or drop authored pitfalls to fit. Never cut, compress or
summarise leaf content to reach a line count — split on a natural seam, or
exceed the target and say so.
`Status`: `planned` → `written` (or `blocked`).
Diagram ids marked `(t)` are rendered as a Markdown table in the note file, not as an SVG.

| # | File | Subject | Tier | Sections | Leaves | Diagrams | Est. | Status | Lines |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `language-substrate/01-basics.md` | Language substrate | BASICS | §1.1, §1.2 | 1.1.1–1.1.10, 1.2.1–1.2.15 (25) | D-001, D-002, D-003, D-004, D-005(t) | 400 | written | 520 |
| 2 | `language-substrate/02-packages-modules-annotations.md` | Packages, modules, annotations, `java.lang` | BASICS | §1.23, §1.24, §1.25 | 1.23.1–1.23.11, 1.24.1–1.24.10, 1.25.1–1.25.13 (34) | D-060, D-061, D-062, D-063(t) | 430 | written | 561 |
| 3 | `language-substrate/03-internals-javac-and-class-file.md` | `javac` pipeline | INTERNALS | §3.1 | 3.1.1, 3.1.4, 3.1.6, 3.1.8, 3.1.9, 3.1.10, 3.1.12 (7) | D-090, D-091, D-092(t) | 400 | written | 588 |
| 3a | `language-substrate/03a-internals-class-file-format.md` | The class file format | INTERNALS | §3.1 | 3.1.2, 3.1.3, 3.1.5, 3.1.7, 3.1.11, 3.1.13, 3.1.14 (7) | — | — | written (split of 3) | 388 |
| 4 | `language-substrate/04-internals-version-history.md` | Version history through 17 | INTERNALS | §3.17 | 3.17.1–3.17.13 (13) | D-129(t) | 380 | written | 577 |
| 4a | `language-substrate/04a-internals-version-history-18-onward.md` | Version history, 18 onward | INTERNALS | §3.17 | 3.17.14–3.17.20 (7) | — | — | written (split of 4) | 353 |
| 5 | `language-substrate/05-internals-observability.md` | Observability toolkit | INTERNALS | §3.18 | 3.18.1–3.18.13 (13) | none | 320 | written | 498 |
| 6 | `primitives-and-conversions/01-basics.md` | Primitives — kinds, defaults, `char` | BASICS | §1.3 | 1.3.1–1.3.4, 1.3.17–1.3.19 (7) | D-006(t), D-010(t) | 430 | written | 508 |
| 6a | `primitives-and-conversions/01a-integral-arithmetic.md` | Two's complement, overflow, division | BASICS | §1.3 | 1.3.5–1.3.9, 1.3.21 (6) | D-007 | — | written (split of 6) | 516 |
| 6b | `primitives-and-conversions/01b-shifts-and-unsigned.md` | Shifts and unsigned operations | BASICS | §1.3 | 1.3.10–1.3.12, 1.3.20 (4) | D-008 | — | written (split of 6) | 435 |
| 6c | `primitives-and-conversions/01c-floating-point.md` | Floating point | BASICS | §1.3 | 1.3.13–1.3.16 (4) | D-009 | — | written (split of 6) | 447 |
| 7 | `primitives-and-conversions/02-operators-and-expressions.md` | Operators, precedence, evaluation order | BASICS | §1.6 | 1.6.1–1.6.5, 1.6.19 (6) | D-015(t) | 420 | written | 597 |
| 7a | `primitives-and-conversions/02a-assignment-and-bitwise.md` | Assignment and bitwise operators | BASICS | §1.6 | 1.6.6–1.6.9 (4) | D-016 | — | written (split of 7) | 508 |
| 7b | `primitives-and-conversions/02b-casts-and-comparison.md` | Casts and comparison | BASICS | §1.6 | 1.6.14–1.6.15 (2) | D-017 | — | written (split of 7) | 399 |
| 7c | `primitives-and-conversions/02c-conditional-operator.md` | The conditional operator | BASICS | §1.6 | 1.6.10–1.6.13 (4) | D-018 | — | written (split of 7) | 449 |
| 7d | `primitives-and-conversions/02d-string-concatenation.md` | `String` concatenation operator | BASICS | §1.6 | 1.6.16–1.6.18 (3) | — | — | written (split of 7) | 393 |
| 8 | `primitives-and-conversions/03-conversions-and-contexts.md` | Conversions and contexts | BASICS | §1.7 | 1.7.1–1.7.6, 1.7.11–1.7.12 (8) | D-019(t), D-021 | 400 | written | 519 |
| 8a | `primitives-and-conversions/03a-promotion-boxing-and-inference.md` | Promotion, boxing, inference | BASICS | §1.7 | 1.7.7–1.7.10, 1.7.13–1.7.17 (9) | D-020, D-022(t) | — | written (split of 8) | 597 |
| 9 | `control-flow/01-basics.md` | Control flow — loops, branches, abrupt completion | BASICS | §1.8 | 1.8.1–1.8.5 (5) | D-023 | 380 | written | 587 |
| 9a | `control-flow/01a-switch.md` | Classic `switch` | BASICS | §1.8 | 1.8.6–1.8.7 (2) | — | — | written (split of 9) | 393 |
| 9b | `control-flow/01b-string-and-enum-switch.md` | `String` and `enum` switch | BASICS | §1.8 | 1.8.8–1.8.10 (3) | D-024 | — | written (split of 9) | 608 |
| 9c | `control-flow/01c-switch-expressions-and-patterns.md` | Switch expressions and patterns | BASICS | §1.8 | 1.8.11–1.8.12 (2) | — | — | written (split of 9) | 520 |
| 9d | `control-flow/01d-assertions-and-synchronized.md` | Assertions and `synchronized` | BASICS | §1.8 | 1.8.13–1.8.14 (2) | — | — | written (split of 9) | 468 |
| 9e | `control-flow/01e-try-and-unreachable-code.md` | `try`/`finally` and unreachable code | BASICS | §1.8 | 1.8.15–1.8.16 (2) | — | — | written (split of 9) | 492 |
| 10 | `wrappers-and-boxing/01-basics.md` | Wrappers and autoboxing | BASICS | §1.9 | 1.9.1–1.9.2 (2) | — | 430 | written | 834 |
| 10a | `wrappers-and-boxing/01a-the-wrapper-caches.md` | The wrapper caches | BASICS | §1.9 | 1.9.3–1.9.4 (2) | D-025 | — | written (split of 10) | 769 |
| 10a2 | `wrappers-and-boxing/01a2-the-archived-cache.md` | The CDS-archived cache | BASICS | §1.9 | 1.9.5 (1) | — | — | written (split of 10) | 646 |
| 10b | `wrappers-and-boxing/01b-cache-coverage-and-reference-equality.md` | Cache coverage, reference equality | BASICS | §1.9 | 1.9.6–1.9.8 (3) | D-026(t) | — | written (split of 10) | 898 |
| 10c | `wrappers-and-boxing/01c-unboxing-null.md` | Unboxing and null | BASICS | §1.9 | 1.9.9–1.9.10 (2) | D-027 | — | written (split of 10) | 838 |
| 10d | `wrappers-and-boxing/01d-wrapper-equals-and-hashcode.md` | Wrapper `equals`/`hashCode` | BASICS | §1.9 | 1.9.11, 1.9.18 (2) | — | — | written (split of 10) | 900 |
| 10e | `wrappers-and-boxing/01e-valueof-and-the-deprecated-constructors.md` | `valueOf`, deprecated constructors | BASICS | §1.9 | 1.9.13 (1) | — | — | written (split of 10) | 662 |
| 10e2 | `wrappers-and-boxing/01e2-parseint-versus-valueof-string.md` | `parseInt` vs `valueOf(String)` | BASICS | §1.9 | 1.9.15 (1) | — | — | written (split of 10) | 857 |
| 10f | `wrappers-and-boxing/01f-parsing-traps-and-the-statics.md` | Parsing traps, the statics | BASICS | §1.9 | 1.9.14, 1.9.16–1.9.17 (3) | — | — | written (split of 10) | 899 |
| 10g | `wrappers-and-boxing/01g-the-cost-of-boxing.md` | The cost of boxing | BASICS | §1.9 | 1.9.12, 1.9.19 (2) | D-028 | — | written (split of 10) | 894 |
| 10h | `wrappers-and-boxing/01h-when-boxing-is-unavoidable.md` | When boxing is unavoidable | BASICS | §1.9 | 1.9.20 (1) | — | — | written (split of 10) | 851 |
| 11 | `wrappers-and-boxing/03-internals-boxing.md` | Boxing internals | INTERNALS | §3.4 | 3.4.1–3.4.2 (2) | D-102 | 380 | written | 694 |
| 11a | `wrappers-and-boxing/03a-internals-cache-configuration-and-cds.md` | Cache configuration and CDS | INTERNALS | §3.4 | 3.4.3–3.4.4 (2) | — | — | written (split of 11) | 750 |
| 11b | `wrappers-and-boxing/03b-internals-the-other-wrapper-caches.md` | The other wrapper caches | INTERNALS | §3.4 | 3.4.5–3.4.6 (2) | — | — | written (split of 11) | 841 |
| 11c | `wrappers-and-boxing/03c-internals-boxing-bytecode.md` | Boxing bytecode | INTERNALS | §3.4 | 3.4.7 (1) | — | — | written (split of 11) | 808 |
| 11d | `wrappers-and-boxing/03d-internals-escape-analysis.md` | Escape analysis | INTERNALS | §3.4 | 3.4.8–3.4.9 (2) | D-103 | — | written (split of 11) | 602 |
| 11e | `wrappers-and-boxing/03e-internals-wrapper-memory.md` | Wrapper memory | INTERNALS | §3.4 | 3.4.10–3.4.12 (3) | — | — | written (split of 11) | 658 |
| 11f | `wrappers-and-boxing/03f-internals-monitors-and-valhalla.md` | Monitors and Valhalla | INTERNALS | §3.4 | 3.4.13–3.4.14 (2) | — | — | written (split of 11) | 820 |
| 12 | `strings/01-basics.md` | `String` API | BASICS | §1.10 | 1.10.1–1.10.23 (23) | D-029, D-030, D-031 | 450 | written | 530 |
| 12b | `strings/01b-the-string-pool.md` | The `String` pool and folding | BASICS | §1.10, §1.11 | 1.10.24, 1.11.1–1.11.9 (10) | D-032, D-033 | — | written (split of 12) | 290 |
| 13 | `strings/02-performance-and-text.md` | `String` performance | INTERMEDIATE | §2.2 | 2.2.1–2.2.12, 2.2.25 (13) | D-065, D-066 | 450 | written | 524 |
| 13b | `strings/02b-text-and-encoding.md` | Text and encoding | INTERMEDIATE | §2.2 | 2.2.13–2.2.24 (12) | D-067, D-068 | — | written (split of 13) | 471 |
| 14 | `strings/03-internals-string.md` | `String` internals — field set, compact strings | INTERNALS | §3.2 | 3.2.1–3.2.5, 3.2.16 (6) | D-093 | 450 | written | 387 |
| 14a | `strings/03a-internals-hash-and-equality.md` | `hashCode`, `equals`, `compareTo` internals | INTERNALS | §3.2 | 3.2.6–3.2.10 (5) | D-094, D-095, D-096 | — | written (split of 14) | 442 |
| 14b | `strings/03b-internals-stringtable-and-interning.md` | `StringTable`, interning, deduplication | INTERNALS | §3.2 | 3.2.11–3.2.15, 3.2.17–3.2.19 (8) | D-097, D-098 | — | written (split of 14) | 598 |
| 15 | `strings/04-internals-stringbuilder-and-concat.md` | `StringBuilder` and indified concat | INTERNALS | §3.3 | 3.3.1–3.3.15 (15) | D-099, D-100, D-101 | 400 | written | 598 |
| 16 | `objects-equality-and-lifecycle/01-basics.md` | The object model, `==` vs identity | BASICS | §1.4, §1.12 | 1.4.1–1.4.10, 1.12.1–1.12.2 (12) | D-011 | 450 | written | 440 |
| 16b | `objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md` | The `equals`/`hashCode` contracts (slug predates its retitle) | BASICS | §1.12 | 1.12.3–1.12.8 (6) | D-034, D-035 | — | written (split of 16) | 585 |
| 16c | `objects-equality-and-lifecycle/01c-object-methods.md` | The rest of `Object` | BASICS | §1.12 | 1.12.9–1.12.19 (11) | D-036, D-037 | — | written (split of 16) | 526 |
| 17 | `objects-equality-and-lifecycle/02-copying-and-composite-equality.md` | Copying and aliasing | INTERMEDIATE | §2.8 | 2.8.1–2.8.8 (8) | none | 380 | written | 432 |
| 17a | `objects-equality-and-lifecycle/02a-composite-equality-and-ordering.md` | Composite equality and ordering | INTERMEDIATE | §2.8 | 2.8.9–2.8.14 (6) | none | — | written (split of 17) | 360 |
| 18 | `objects-equality-and-lifecycle/03-lifecycle-and-references.md` | What keeps an object alive | INTERMEDIATE | §2.9 | 2.9.1–2.9.3, 2.9.10 (4) | D-083 | 340 | written | 478 |
| 18a | `objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md` | Finalization, cleanup, leaks | INTERMEDIATE | §2.9 | 2.9.4–2.9.9, 2.9.11 (7) | D-084 | — | written (split of 18) | 607 |
| 19 | `objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md` | `hashCode` and identity internals | INTERNALS | §3.13 | 3.13.1–3.13.9 (9) | D-124 | 320 | written | 442 |
| 20 | `objects-equality-and-lifecycle/05-internals-object-layout.md` | Object layout and memory | INTERNALS | §3.8 | 3.8.1–3.8.13 (13) | D-112 | 360 | written | 471 |
| 21 | `classes-and-initialization/01-basics.md` | Variables and declarations | BASICS | §1.5 | 1.5.1–1.5.4, 1.5.13 (5) | D-012 | 450 | written | 588 |
| 21a | `classes-and-initialization/01a-names-scope-and-var.md` | Names, scope, `var` | BASICS | §1.5 | 1.5.5–1.5.10, 1.5.12 (7) | D-013 | — | written (split of 21) | 650 |
| 21b | `classes-and-initialization/01b-initialization-order.md` | Initialization order of a `new` | BASICS | §1.5, §1.13 | 1.5.11, 1.13.6–1.13.8, 1.13.16 (5) | D-014, D-038 | — | written (split of 21) | 650 |
| 21c | `classes-and-initialization/01c-class-anatomy-and-constructors.md` | Class anatomy and constructors | BASICS | §1.13 | 1.13.1–1.13.5, 1.13.17 (6) | — | — | written (split of 21) | 536 |
| 21d | `classes-and-initialization/01d-class-initialization-triggers.md` | Class initialization triggers and failure | BASICS | §1.13 | 1.13.9–1.13.15 (7) | D-039, D-040 | — | written (split of 21) | 707 |
| 22 | `classes-and-initialization/02-modifiers.md` | Modifiers — `static`, `final`, `abstract` | BASICS | §1.14 | 1.14.1–1.14.11 (11) | D-042 | 420 | written | 812 |
| 22a | `classes-and-initialization/02a-access-and-other-modifiers.md` | Access and remaining modifiers | BASICS | §1.14 | 1.14.12–1.14.20 (9) | D-041(t) | — | written (split of 22) | 844 |
| 23 | `classes-and-initialization/03-internals-class-loading-and-init.md` | Loading, linking, resolution | INTERNALS | §3.6 | 3.6.1–3.6.6 (6) | D-107 | 420 | written | 717 |
| 23a | `classes-and-initialization/03a-internals-class-init-locking-and-failure.md` | Init locking and failure | INTERNALS | §3.6 | 3.6.7–3.6.10 (4) | D-108 | — | written (split of 23) | 744 |
| 23b | `classes-and-initialization/03b-internals-class-loaders-and-identity.md` | Class loaders and type identity | INTERNALS | §3.6 | 3.6.11–3.6.17 (7) | — | — | written (split of 23) | 833 |
| 24 | `classes-and-initialization/04-internals-final-and-constant-folding.md` | `final` semantics and constant folding | INTERNALS | §3.12 | 3.12.1–3.12.11 (11) | D-122, D-123(t) | 350 | written | 716 |
| 25 | `inheritance-and-dispatch/01-basics.md` | Class inheritance and overriding | BASICS | §1.15 | 1.15.1–1.15.5, 1.15.12–1.15.18 (12) | D-044, D-045, D-046 | 450 | written | 866 |
| 25a | `inheritance-and-dispatch/01a-overload-resolution-and-dispatch.md` | Overload resolution (JLS §15.12.2) | BASICS | §1.15 | 1.15.6–1.15.11 (6) | D-043 | — | written (split of 25) | 670 |
| 25b | `inheritance-and-dispatch/01b-interfaces.md` | Interfaces, defaults, diamond | BASICS | §1.16 | 1.16.1–1.16.12 (12) | D-047(t), D-048 | — | written (split of 25) | 648 |
| 26 | `inheritance-and-dispatch/02-nested-classes.md` | Nested, inner, local, anonymous | BASICS | §1.17 | 1.17.1–1.17.13 (13) | D-049(t), D-050, D-051 | 380 | written | 808 |
| 27 | `inheritance-and-dispatch/03-internals-dispatch.md` | Method dispatch internals | INTERNALS | §3.7 | 3.7.1–3.7.12 (12) | D-109(t), D-110, D-111 | 380 | written | 856 |
| 28 | `inheritance-and-dispatch/04-internals-nested-classes.md` | Nested class internals | INTERNALS | §3.11 | 3.11.1–3.11.12 (12) | D-120, D-121 | 360 | written | 860 |
| 29 | `enums/01-basics.md` | Enums — declaration and basics | BASICS | §1.18 | 1.18.1–1.18.5 (5) | — | 420 | written | 695 |
| 29a | `enums/01a-implicit-members-and-identity.md` | Implicit members and identity | BASICS | §1.18 | 1.18.6–1.18.10 (5) | D-052 | — | written (split of 29) | 898 |
| 29b | `enums/01b-collections-patterns-and-guarantees.md` | Enum collections | BASICS | §1.18 | 1.18.11–1.18.13 (3) | — | — | written (split of 29) | 795 |
| 29c | `enums/01c-production-patterns-and-guarantees.md` | Production patterns and guarantees | BASICS | §1.18 | 1.18.14–1.18.17 (4) | — | — | written (split of 29) | 638 |
| 30 | `enums/03-internals-enums.md` | Enum desugaring | INTERNALS | §3.10 | 3.10.1–3.10.3 (3) | D-117 | 400 | written | 600 |
| 30a | `enums/03a-internals-enum-members.md` | Implicit member bytecode | INTERNALS | §3.10 | 3.10.4–3.10.6 (3) | — | — | written (split of 30) | 581 |
| 30b | `enums/03b-internals-guarantees-and-switch.md` | Guarantees and `$SwitchMap` | INTERNALS | §3.10 | 3.10.7–3.10.9 (3) | D-118 | — | written (split of 30) | 708 |
| 30c | `enums/03c-internals-enumset-enummap.md` | `EnumSet` and `EnumMap` internals | INTERNALS | §3.10 | 3.10.10–3.10.12 (3) | D-119 | — | written (split of 30) | 756 |
| 30d | `enums/03d-internals-enum-evolution.md` | Enum evolution and serialization | INTERNALS | §3.10 | 3.10.13–3.10.14 (2) | — | — | written (split of 30) | 426 |
| 31 | `records-and-sealed/01-basics.md` | Records | BASICS | §1.19 | 1.19.1–1.19.3 (3) | — | 260 | written | 760 |
| 31a | `records-and-sealed/01a-object-methods-sealed-and-fit.md` | Generated methods, sealed types, fit | BASICS | §1.19 | 1.19.4–1.19.6 (3) | — | — | written (split of 31) | 798 |
| 32 | `exceptions/01-basics.md` | The exception model | BASICS | §1.20 | 1.20.1–1.20.6 (6) | D-053 | 450 | written | 520 |
| 32a | `exceptions/01a-throwable-api-and-chaining.md` | `Throwable` API and chaining | BASICS | §1.20 | 1.20.7–1.20.8 (2) | — | — | written (split of 32) | 586 |
| 32b | `exceptions/01b-catch-multicatch-and-precise-rethrow.md` | `catch`, multi-catch, precise rethrow | BASICS | §1.20 | 1.20.9–1.20.11 (3) | — | — | written (split of 32) | 627 |
| 32c | `exceptions/01c-try-with-resources-and-suppression.md` | Try-with-resources, suppression | BASICS | §1.20 | 1.20.12–1.20.15 (4) | D-054 | — | written (split of 32) | 594 |
| 32d | `exceptions/01d-finally-traps.md` | `finally` traps | BASICS | §1.20 | 1.20.16–1.20.17, 1.20.21 (3) | D-055 | — | written (split of 32) | 648 |
| 32e | `exceptions/01e-catch-discipline-and-top-level-handling.md` | Catch discipline, top-level handling | BASICS | §1.20 | 1.20.18–1.20.20, 1.20.22–1.20.24 (6) | — | — | written (split of 32) | 599 |
| 33 | `exceptions/02-in-practice.md` | Exceptions in practice | INTERMEDIATE | §2.6 | 2.6.1–2.6.2, 2.6.5, 2.6.8 (4) | D-081 | 430 | written | 636 |
| 33a | `exceptions/02a-checked-exceptions-and-lambdas.md` | Checked exceptions and lambdas | INTERMEDIATE | §2.6 | 2.6.3–2.6.4 (2) | — | — | written (split of 33) | 594 |
| 33b | `exceptions/02b-designing-an-exception-hierarchy.md` | Designing an exception hierarchy | INTERMEDIATE | §2.6 | 2.6.6–2.6.7, 2.6.9–2.6.10 (4) | D-082 | — | written (split of 33) | 860 |
| 33c | `exceptions/02c-cost-and-control-flow.md` | Cost and control flow | INTERMEDIATE | §2.6 | 2.6.11–2.6.13, 2.6.20–2.6.21 (5) | — | — | written (split of 33) | 690 |
| 33d | `exceptions/02d-logging-and-api-boundaries.md` | Logging and API boundaries | INTERMEDIATE | §2.6 | 2.6.14–2.6.16 (3) | — | — | written (split of 33) | 646 |
| 33e | `exceptions/02e-resources-interrupts-and-testing.md` | Resources, interrupts, testing | INTERMEDIATE | §2.6 | 2.6.17–2.6.19, 2.6.22–2.6.23 (5) | — | — | written (split of 33) | 655 |
| 34 | `exceptions/03-internals-exception-mechanics.md` | Exception mechanics — the exception table | INTERNALS | §3.9 | 3.9.1–3.9.2, 3.9.5 (3) | D-113 | 430 | written | 582 |
| 34a | `exceptions/03a-internals-finally-and-twr-desugaring.md` | `finally` and try-with-resources desugaring | INTERNALS | §3.9 | 3.9.3–3.9.4 (2) | D-114 | — | written (split of 34) | 671 |
| 34b | `exceptions/03b-internals-stack-trace-capture.md` | Stack-trace capture | INTERNALS | §3.9 | 3.9.6–3.9.8, 3.9.15 (4) | D-115 | — | written (split of 34) | 755 |
| 34c | `exceptions/03c-internals-fast-throw-and-truncation.md` | Fast-throw and truncation | INTERNALS | §3.9 | 3.9.9–3.9.10, 3.9.14 (3) | D-116 | — | written (split of 34) | 503 |
| 34d | `exceptions/03d-internals-npe-messages-and-diagnostics.md` | Helpful NPE messages, diagnostics | INTERNALS | §3.9 | 3.9.11–3.9.13, 3.9.16–3.9.17 (5) | — | — | written (split of 34) | 740 |
| 35 | `generics/01-basics.md` | Generics basics | BASICS | §1.21 | 1.21.1–1.21.6 (6) | — | 440 | written | 454 |
| 35a | `generics/01a-erasure-and-its-consequences.md` | Erasure and its consequences | BASICS | §1.21 | 1.21.7–1.21.8, 1.21.17 (3) | — | — | written (split of 35) | 514 |
| 35b | `generics/01b-variance-and-wildcards.md` | Variance and wildcards | BASICS | §1.21 | 1.21.9–1.21.14 (6) | D-056, D-057 | — | written (split of 35) | 461 |
| 35c | `generics/01c-raw-types-and-unchecked-warnings.md` | Raw types, unchecked warnings | BASICS | §1.21 | 1.21.15–1.21.16, 1.21.18–1.21.19 (4) | — | — | written (split of 35) | 585 |
| 35d | `generics/01d-recursive-bounds-and-heterogeneous-containers.md` | Recursive bounds, heterogeneous containers | BASICS | §1.21 | 1.21.20–1.21.21 (2) | — | — | written (split of 35) | 606 |
| 36 | `generics/02-in-anger.md` | Generics in anger | INTERMEDIATE | §2.7 | 2.7.1–2.7.4 (4) | — | 400 | written | 525 |
| 36a | `generics/02a-type-tokens-and-generic-reflection.md` | Type tokens, generic reflection | INTERMEDIATE | §2.7 | 2.7.5–2.7.7 (3) | — | — | written (split of 36) | 548 |
| 36b | `generics/02b-generic-arrays-and-self-types.md` | Generic arrays, self types | INTERMEDIATE | §2.7 | 2.7.8–2.7.10 (3) | — | — | written (split of 36) | 865 |
| 36c | `generics/02c-inference-and-generic-limits.md` | Inference and generic limits | INTERMEDIATE | §2.7 | 2.7.11–2.7.15 (5) | — | — | written (split of 36) | 558 |
| 36d | `generics/02d-migration-and-reading-signatures.md` | Migration, reading signatures | INTERMEDIATE | §2.7 | 2.7.16–2.7.18 (3) | — | — | written (split of 36) | 429 |
| 37 | `generics/03-internals-erasure.md` | Erasure internals | INTERNALS | §3.5 | 3.5.1–3.5.2 (2) | D-104 | 420 | written | 453 |
| 37a | `generics/03a-internals-bridge-methods.md` | Bridge methods | INTERNALS | §3.5 | 3.5.3–3.5.6 (4) | D-105 | — | written (split of 37) | 494 |
| 37b | `generics/03b-internals-reifiable-types-and-generic-arrays.md` | Reifiable types, generic arrays | INTERNALS | §3.5 | 3.5.7–3.5.8 (2) | — | — | written (split of 37) | 732 |
| 37c | `generics/03c-internals-heap-pollution-and-safevarargs.md` | Heap pollution, `@SafeVarargs` | INTERNALS | §3.5 | 3.5.9–3.5.10 (2) | D-106 | — | written (split of 37) | 788 |
| 37d | `generics/03d-internals-erasure-limits-and-capture.md` | Erasure limits, capture | INTERNALS | §3.5 | 3.5.11–3.5.13 (3) | — | — | written (split of 37) | 543 |
| 37e | `generics/03e-internals-why-erasure-and-super-type-tokens.md` | Why erasure, super type tokens | INTERNALS | §3.5 | 3.5.14–3.5.16 (3) | — | — | written (split of 37) | 516 |
| 38 | `arrays/01-basics.md` | Arrays | BASICS | §1.22 | 1.22.1–1.22.4 (4) | — | 380 | written | 555 |
| 38a | `arrays/01a-covariance-and-mutability.md` | Covariance and mutability | BASICS | §1.22 | 1.22.5–1.22.7 (3) | — | — | written (split of 38) | 580 |
| 38b | `arrays/01b-array-utilities-and-arraycopy.md` | Array utilities, `arraycopy` | BASICS | §1.22 | 1.22.8–1.22.10 (3) | — | — | written (split of 38) | 461 |
| 38c | `arrays/01c-memory-layout-and-bounds.md` | Memory layout and bounds | BASICS | §1.22 | 1.22.11–1.22.13 (3) | D-058 | — | written (split of 38) | 433 |
| 38d | `arrays/01d-varargs-and-choosing-arrays.md` | Varargs, choosing arrays | BASICS | §1.22 | 1.22.14–1.22.16 (3) | D-059 | — | written (split of 38) | 767 |
| 39 | `cost-model/02-master-cost-table.md` | The master cost model | INTERMEDIATE | §2.1 | 2.1.1–2.1.3 (3) | D-064(t) | 300 | written | 644 |
| 39a | `cost-model/02a-measurement-and-amortisation.md` | Measurement and amortisation | INTERMEDIATE | §2.1 | 2.1.4–2.1.7 (4) | — | — | written (split of 39) | 704 |
| 40 | `immutability-and-design/02-immutability.md` | Immutability design | INTERMEDIATE | §2.3 | 2.3.1–2.3.5 (5) | D-069, D-070 | 400 | written | 784 |
| 40a | `immutability-and-design/02a-shallow-deep-and-building-blocks.md` | Shallow vs deep, building blocks | INTERMEDIATE | §2.3 | 2.3.6–2.3.10 (5) | — | — | written (split of 40) | 882 |
| 40b | `immutability-and-design/02b-records-jmm-and-builders.md` | Records, the JMM, builders | INTERMEDIATE | §2.3 | 2.3.11–2.3.13 (3) | — | — | written (split of 40) | 625 |
| 40c | `immutability-and-design/02c-unsafe-immutables-builders-and-interning.md` | Unsafe immutables, interning | INTERMEDIATE | §2.3 | 2.3.14–2.3.16 (3) | — | — | written (split of 40) | 657 |
| 41 | `immutability-and-design/03-pass-by-value.md` | Pass-by-value | INTERMEDIATE | §2.13 | 2.13.1–2.13.9 (9) | D-088 | 300 | written | 746 |
| 42 | `immutability-and-design/04-design-idioms.md` | Design idioms | INTERMEDIATE | §2.14 | 2.14.1–2.14.5 (5) | — | 380 | written | 891 |
| 42a | `immutability-and-design/04a-composition-and-cross-index.md` | Composition and cross-index | INTERMEDIATE | §2.14 | 2.14.6–2.14.12 (7) | — | — | written (split of 42) | 900 |
| 43 | `immutability-and-design/05-which-construct.md` | Which construct do I reach for | INTERMEDIATE | §2.15 | 2.15.1–2.15.5 (5) | D-089 | 320 | written | 756 |
| 43a | `immutability-and-design/05a-text-time-copy-and-nested.md` | Text, time, copy, nested | INTERMEDIATE | §2.15 | 2.15.6–2.15.10 (5) | — | — | written (split of 43) | 774 |
| 44 | `numbers-and-money/02-numbers-and-money.md` | Numbers and money | INTERMEDIATE | §2.4 | 2.4.1–2.4.4 (4) | D-071, D-080(t) | 450 | written | 719 |
| 44a | `numbers-and-money/02f-double-comparison-and-float-choice.md` | `double` comparison, choosing float | INTERMEDIATE | §2.4 | 2.4.5–2.4.6 (2) | — | — | written (split of 44) | 467 |
| 44b | `numbers-and-money/02a-bigdecimal-structure-and-construction.md` | `BigDecimal` structure, construction | INTERMEDIATE | §2.4 | 2.4.7–2.4.10 (4) | D-072 | — | written (split of 44) | 708 |
| 44c | `numbers-and-money/02b-equality-scale-and-rounding.md` | Equality, scale, rounding | INTERMEDIATE | §2.4 | 2.4.11–2.4.12 (2) | D-073 | — | written (split of 44) | 573 |
| 44d | `numbers-and-money/02g-rounding-modes-and-the-api-surface.md` | Rounding modes, API surface | INTERMEDIATE | §2.4 | 2.4.13–2.4.15 (3) | D-074 | — | written (split of 44) | 704 |
| 44e | `numbers-and-money/02c-mathcontext-constants-and-minor-units.md` | `MathContext`, constants, minor units | INTERMEDIATE | §2.4 | 2.4.16–2.4.19 (4) | — | — | written (split of 44) | 880 |
| 44f | `numbers-and-money/02d-storage-biginteger-and-cost.md` | Storage, `BigInteger`, cost | INTERMEDIATE | §2.4 | 2.4.20–2.4.22 (3) | — | — | written (split of 44) | 553 |
| 44g | `numbers-and-money/02e-parsing-and-formatting-numbers.md` | Parsing and formatting numbers | INTERMEDIATE | §2.4 | 2.4.23–2.4.24 (2) | — | — | written (split of 44) | 510 |
| 45 | `numbers-and-money/03-internals-bigdecimal.md` | `BigDecimal` internals — field set | INTERNALS | §3.14 | 3.14.1–3.14.4 (4) | D-125 | 370 | written | 627 |
| 45a | `numbers-and-money/03a-internals-bigdecimal-arithmetic-and-equality.md` | `BigDecimal` arithmetic, equality | INTERNALS | §3.14 | 3.14.5–3.14.9 (5) | — | — | written (split of 45) | 671 |
| 45b | `numbers-and-money/03b-internals-biginteger-and-long-cents.md` | `BigInteger`, long-cents | INTERNALS | §3.14 | 3.14.10–3.14.13 (4) | — | — | written (split of 45) | 604 |
| 46 | `numbers-and-money/04-internals-floating-point.md` | Floating point internals | INTERNALS | §3.15 | 3.15.1–3.15.5 (5) | — | 390 | written | 550 |
| 46a | `numbers-and-money/04a-internals-ulp-rounding-and-tostring.md` | ULP, rounding, `toString` | INTERNALS | §3.15 | 3.15.6–3.15.8 (3) | D-126 | — | written (split of 46) | 529 |
| 46b | `numbers-and-money/04b-internals-strictfp-strictmath-and-fma.md` | `strictfp`, `StrictMath`, FMA | INTERNALS | §3.15 | 3.15.9–3.15.11 (3) | — | — | written (split of 46) | 582 |
| 46c | `numbers-and-money/04c-internals-summation-narrowing-and-fit.md` | Summation, narrowing, fit | INTERNALS | §3.15 | 3.15.12–3.15.14 (3) | — | — | written (split of 46) | 619 |
| 47 | `date-and-time/02-date-and-time.md` | Date and time — the type map | INTERMEDIATE | §2.5 | 2.5.1–2.5.4 (4) | D-075 | 450 | written | 494 |
| 47a | `date-and-time/02a-instant-local-and-zoned.md` | `Instant`, local, zoned | INTERMEDIATE | §2.5 | 2.5.5–2.5.6, 2.5.11–2.5.12 (4) | — | — | written (split of 47) | 575 |
| 47b | `date-and-time/02b-amounts-dst-and-tzdb.md` | Amounts, DST, tzdb | INTERMEDIATE | §2.5 | 2.5.7–2.5.10, 2.5.13 (5) | D-077, D-078 | — | written (split of 47) | 644 |
| 47c | `date-and-time/02c-temporal-arithmetic-and-adjusters.md` | Temporal arithmetic, adjusters | INTERMEDIATE | §2.5 | 2.5.14–2.5.17 (4) | D-079 | — | written (split of 47) | 618 |
| 47d | `date-and-time/02d-formatting-and-parsing.md` | Formatting and parsing | INTERMEDIATE | §2.5 | 2.5.18–2.5.22 (5) | D-076(t) | — | written (split of 47) | 364 |
| 47e | `date-and-time/02e-clock-precision-and-storage.md` | `Clock`, precision, storage | INTERMEDIATE | §2.5 | 2.5.23–2.5.27 (5) | — | — | written (split of 47) | 387 |
| 48 | `date-and-time/03-internals-java-time.md` | `java.time` internals | INTERNALS | §3.16 | 3.16.1–3.16.4 (4) | D-127 | 390 | written | 625 |
| 48a | `date-and-time/03a-internals-zonerules-and-tzdb.md` | `ZoneRules` and the tzdb | INTERNALS | §3.16 | 3.16.5–3.16.7 (3) | D-128 | — | written (split of 48) | 588 |
| 48b | `date-and-time/03b-internals-temporal-spi-and-formatter.md` | Temporal SPI, formatter | INTERNALS | §3.16 | 3.16.8–3.16.10 (3) | — | — | written (split of 48) | 642 |
| 48c | `date-and-time/03c-internals-precision-scale-and-legacy-bridging.md` | Precision, scale, legacy bridging | INTERNALS | §3.16 | 3.16.11–3.16.14 (4) | — | — | written (split of 48) | 686 |
| 49 | `serialization/02-serialization.md` | Serialization | INTERMEDIATE | §2.10 | 2.10.1–2.10.3, 2.10.13 (4) | — | 380 | written | 441 |
| 49a | `serialization/02a-magic-methods-and-constructor-bypass.md` | Magic methods, constructor bypass | INTERMEDIATE | §2.10 | 2.10.4–2.10.7 (4) | D-085 | — | written (split of 49) | 779 |
| 49b | `serialization/02b-externalizable-records-and-lambdas.md` | `Externalizable`, records, lambdas | INTERMEDIATE | §2.10 | 2.10.8–2.10.9, 2.10.14 (3) | — | — | written (split of 49) | 696 |
| 49c | `serialization/02c-attack-surface-filters-and-the-practical-rule.md` | Attack surface, filters, the rule | INTERMEDIATE | §2.10 | 2.10.10–2.10.12 (3) | — | — | written (split of 49) | 676 |
| 50 | `null-discipline/02-null-discipline.md` | Null discipline | INTERMEDIATE | §2.11 | 2.11.1, 2.11.10–2.11.11 (3) | — | 330 | written | 734 |
| 50a | `null-discipline/02a-optional-and-defaulting.md` | `Optional` and defaulting | INTERMEDIATE | §2.11 | 2.11.2–2.11.4, 2.11.6 (4) | D-086 | — | written (split of 50) | 647 |
| 50b | `null-discipline/02b-null-object-annotations-and-diagnosis.md` | Null object, annotations, diagnosis | INTERMEDIATE | §2.11 | 2.11.5, 2.11.7–2.11.9 (4) | — | — | written (split of 50) | 759 |
| 51 | `reflection/02-reflection.md` | Reflection and dynamic access | INTERMEDIATE | §2.12 | 2.12.1–2.12.3 (3) | D-087(t) | 350 | written | 500 |
| 51a | `reflection/02a-access-cost-and-method-handles.md` | Access cost, `MethodHandle` | INTERMEDIATE | §2.12 | 2.12.4–2.12.6 (3) | — | — | written (split of 51) | 458 |
| 51b | `reflection/02b-proxies-frameworks-and-generics.md` | Proxies, frameworks, generics | INTERMEDIATE | §2.12 | 2.12.7–2.12.9 (3) | — | — | written (split of 51) | 428 |
| 51c | `reflection/02c-final-fields-and-security-surface.md` | `final` fields, security surface | INTERMEDIATE | §2.12 | 2.12.10–2.12.11 (2) | — | — | written (split of 51) | 520 |
| 52 | `build-it/01-mystring-and-mystringbuilder.md` | `MyString` | BUILD | §4.1 | 4.1.1–4.1.3, 4.1.5 (4) | D-130 | 450 | written | 865 |
| 52a | `build-it/01a-mystring-intern-pool-and-diff.md` | `MyString` intern pool, diff | BUILD | §4.1 | 4.1.4, 4.1.6 (2) | — | — | written (split of 52) | 624 |
| 52b | `build-it/01b-mystringbuilder.md` | `MyStringBuilder` | BUILD | §4.2 | 4.2.1–4.2.4 (4) | D-131 | — | written (split of 52) | 855 |
| 52c | `build-it/01c-mystringbuilder-cost-and-diff.md` | `MyStringBuilder` cost, diff | BUILD | §4.2 | 4.2.5–4.2.6 (2) | — | — | written (split of 52) | 536 |
| 53 | `build-it/02-myinteger-and-generics.md` | `MyInteger` | BUILD | §4.3 | 4.3.1–4.3.5 (5) | D-132 | 460 | written | 846 |
| 53a | `build-it/02a-generic-containers.md` | Generic containers | BUILD | §4.4 | 4.4.1–4.4.3 (3) | D-133 | — | written (split of 53) | 859 |
| 53b | `build-it/02b-typesafe-container-and-generic-stack.md` | Typesafe container, generic stack | BUILD | §4.4 | 4.4.4–4.4.5 (2) | — | — | written (split of 53) | 678 |
| 53c | `build-it/02c-generic-builders-tokens-and-varargs.md` | Generic builders, tokens, varargs | BUILD | §4.4 | 4.4.6–4.4.7 (2) | — | — | written (split of 53) | 839 |
| 53d | `build-it/02d-wildcard-copy-varargs-and-diff.md` | Wildcard copy, varargs, diff | BUILD | §4.4 | 4.4.8–4.4.10 (3) | — | — | written (split of 53) | 712 |
| 54 | `build-it/03-enums-exceptions-resources.md` | Typesafe enum build | BUILD | §4.5 | 4.5.1 (1) | — | 460 | written | 682 |
| 54a | `build-it/03k-persisted-code-enum.md` | Persisted-code enum | BUILD | §4.5 | 4.5.2 (1) | — | — | written (split of 54) | 663 |
| 54b | `build-it/03f-strategy-enum.md` | Strategy enum | BUILD | §4.5 | 4.5.3 (1) | — | — | written (split of 54) | 826 |
| 54c | `build-it/03a-enum-state-machine-and-singleton.md` | Enum state machine | BUILD | §4.5 | 4.5.4 (1) | D-134 | — | written (split of 54) | 716 |
| 54d | `build-it/03g-enum-singleton.md` | Enum singleton | BUILD | §4.5 | 4.5.5 (1) | — | — | written (split of 54) | 684 |
| 54e | `build-it/03b-enum-values-cache-and-diff.md` | `values()` cache, diff | BUILD | §4.5 | 4.5.6–4.5.7 (2) | — | — | written (split of 54) | 900 |
| 54f | `build-it/03c-exception-hierarchy-and-stackless.md` | Exception hierarchy (1 of 3) | BUILD | §4.6 | 4.6.1 part 1 | — | — | written (split of 54) | 791 |
| 54g | `build-it/03m-exception-context-and-null-policy.md` | Context, null policy (2 of 3) | BUILD | §4.6 | 4.6.1 part 2 | — | — | written (split of 54) | 453 |
| 54h | `build-it/03n-exception-boundaries-and-serialization.md` | Boundaries, serial form (3 of 3) | BUILD | §4.6 | 4.6.1 part 3 | — | — | written (split of 54) | 453 |
| 54i | `build-it/03h-stackless-exception.md` | Stackless exception | BUILD | §4.6 | 4.6.2 (1) | — | — | written (split of 54) | 839 |
| 54j | `build-it/03d-autocloseable-and-finally.md` | `AutoCloseable` and `finally` | BUILD | §4.6 | 4.6.3 (1) | — | — | written (split of 54) | 753 |
| 54k | `build-it/03l-finally-destroys-the-primary.md` | `finally` destroys the primary | BUILD | §4.6 | 4.6.4 (1) | — | — | written (split of 54) | 658 |
| 54l | `build-it/03e-checked-crossing-cleaner-and-diff.md` | Checked crossing, diff | BUILD | §4.6 | 4.6.5–4.6.6 (2) | — | — | written (split of 54) | 897 |
| 54m | `build-it/03j-cleaner-and-diff.md` | `Cleaner`, diff | BUILD | §4.6 | 4.6.7, 4.6.9 (2) | — | — | written (split of 54) | 857 |
| 54n | `build-it/03i-finally-return-harness.md` | `finally`/`return` harness | BUILD | §4.6 | 4.6.8 (1) | — | — | written (split of 54) | 899 |
| 55 | `build-it/04-value-objects-and-money.md` | Value objects and money | BUILD | §4.7 | 4.7.1–4.7.2 (2) | D-135 | 400 | written | 898 |
| 55a | `build-it/04c-allocation-and-rounding-bias.md` | Allocation and precision | BUILD | §4.7 | 4.7.3 part 1 | — | — | written (split of 55) | 749 |
| 55b | `build-it/04e-rounding-bias-experiment.md` | Rounding-bias experiment | BUILD | §4.7 | 4.7.3 part 2 | — | — | written (split of 55) | 688 |
| 55c | `build-it/04a-defensive-copying-and-collections.md` | Defensive copying, collections | BUILD | §4.7 | 4.7.4–4.7.5 (2) | — | — | written (split of 55) | 899 |
| 55d | `build-it/04b-deep-copy-and-clock-injection.md` | Deep copy | BUILD | §4.7 | 4.7.6 (1) | — | — | written (split of 55) | 854 |
| 55e | `build-it/04f-clock-injection.md` | `Clock` injection | BUILD | §4.7 | 4.7.7 (1) | — | — | written (split of 55) | 568 |
| 55f | `build-it/04d-value-object-diff.md` | Value-object diff | BUILD | §4.7 | 4.7.8 (1) | — | — | written (split of 55) | 899 |
| 56 | `build-it/05-diagnostic-harnesses.md` | Puzzler harness, snippets 1–8 | BUILD | §4.8 | 4.8.1 part 1 | — | 450 | written | 703 |
| 56a | `build-it/05f-puzzler-harness-part-two.md` | Puzzler harness, snippets 9–15 | BUILD | §4.8 | 4.8.1 part 2 | — | — | written (split of 56) | 692 |
| 56b | `build-it/05a-construction-and-init-harnesses.md` | Construction and init harnesses | BUILD | §4.8 | 4.8.2 (1) | — | — | written (split of 56) | 625 |
| 56c | `build-it/05g-class-initialization-order.md` | Class initialization order | BUILD | §4.8 | 4.8.3 (1) | — | — | written (split of 56) | 785 |
| 56d | `build-it/05e-class-init-deadlock.md` | Class-init deadlock | BUILD | §4.8 | 4.8.4 (1) | — | — | written (split of 56) | 898 |
| 56e | `build-it/05b-inlining-and-retention-harnesses.md` | Inlining and retention | BUILD | §4.8 | 4.8.5 (1) | — | — | written (split of 56) | 899 |
| 56f | `build-it/05h-inner-class-retention.md` | Inner-class retention | BUILD | §4.8 | 4.8.6 (1) | — | — | written (split of 56) | 897 |
| 56g | `build-it/05c-dispatch-and-value-harnesses.md` | Pass-by-value harness (slug overstates) | BUILD | §4.8 | 4.8.7 (1) | — | — | written (split of 56) | 634 |
| 56h | `build-it/05j-overload-resolution-harness.md` | Overload-resolution harness | BUILD | §4.8 | 4.8.8 (1) | — | — | written (split of 56) | 673 |
| 56i | `build-it/05d-concurrency-and-time-harnesses.md` | Concurrency and time harnesses | BUILD | §4.8 | 4.8.9 (1) | — | — | written (split of 56) | 897 |
| 56j | `build-it/05i-dst-harness.md` | DST harness | BUILD | §4.8 | 4.8.10 (1) | — | — | written (split of 56) | 900 |
| 57 | `90-interview-basics.md` | Part 1 wrap-up | INTERVIEW | Part 1 | — (summarises §1.1–§1.25) | — | 400 | written | 341 |
| 58 | `91-interview-intermediate.md` | Part 2 wrap-up | INTERVIEW | Part 2 | — (summarises §2.1–§2.15) | — | 400 | written | 429 |
| 59 | `92-interview-internals.md` | Part 3 wrap-up | INTERVIEW | Part 3 | — (summarises §3.1–§3.18) | — | 400 | written | 344 |
| 60 | `93-interview-build-it.md` | Part 4 wrap-up | INTERVIEW | Part 4 | — (summarises §4.1–§4.8) | — | 380 | written | 375 |
| 61 | `94-interview-questions-and-drills.md` | §5.1 questions 1–16 | INTERVIEW | §5.1 | 5.1.1–5.1.16 | — | 600 | written | 890 |
| 61a | `94a-interview-questions-17-32.md` | §5.1 questions 17–32 | INTERVIEW | §5.1 | 5.1.17–5.1.32 | — | — | written (split of 61) | 532 |
| 61b | `94b-interview-questions-33-48.md` | §5.1 questions 33–48 | INTERVIEW | §5.1 | 5.1.33–5.1.48 | — | — | written (split of 61) | 558 |
| 61c | `94c-interview-questions-49-64.md` | §5.1 questions 49–64 | INTERVIEW | §5.1 | 5.1.49–5.1.64 | — | — | written (split of 61) | 460 |
| 61d | `94d-interview-questions-65-80.md` | §5.1 questions 65–80 | INTERVIEW | §5.1 | 5.1.65–5.1.80 | — | — | written (split of 61) | 430 |
| 61e | `94e-interview-trap-index.md` | The trap index | INTERVIEW | §5.2 | 5.2.1 | D-136(t) | — | written (split of 61) | 675 |
| 61e2 | `94e2-interview-version-stale-and-mistakes.md` | Version-stale claims, expensive mistakes | INTERVIEW | §5.2 | 5.2.2–5.2.4 | D-137(t), D-138(t) | — | written (split of 61) | 633 |
| 61f | `94f-interview-drills-and-retention.md` | Drills, retention, Part 5 wrap-up | INTERVIEW | §5.3 | 5.3.1–5.3.7 | D-139(t) | — | written (split of 61) | 737 |
| 61g | `94g-interview-atomic-concept-checklist.md` | Atomic concept checklist (350 bullets, flat) | INTERVIEW | §5.3 | 5.3.8 | — | — | written (split of 61) | 381 |

Rows 57–60 carry no syllabus leaves of their own: they are the per-part wrap-ups the prompt
requires (summary table + 10 Q&As + 5 predict-the-output puzzles), covering material already
assigned to the rows of that part.

---

## Nav chain

One unbroken chain in row order. Row 1 omits `Previous:`; row 61 omits `Next:`. Each writer
receives its finished nav line verbatim and never derives its own neighbours.

---

## Leaf ledger

Every leaf in the prompt is assigned to exactly one file. The leaf **text** lives in
`src/metadata/prompts/03-java-core-prompt.md` lines 439–2660 (hash recorded above); this ledger
records ownership, which is what the plan needs to guarantee no leaf is orphaned and no leaf is
claimed twice.

| Section | Leaves | Count | Owning file (row) |
|---|---|---|---|
| §1.1 | 1.1.1–1.1.10 | 10 | 1 |
| §1.2 | 1.2.1–1.2.15 | 15 | 1 |
| §1.3 | 1.3.1–1.3.21 | 21 | 6 |
| §1.4 | 1.4.1–1.4.10 | 10 | 16 |
| §1.5 | 1.5.1–1.5.13 | 13 | 21 |
| §1.6 | 1.6.1–1.6.19 | 19 | 7 |
| §1.7 | 1.7.1–1.7.17 | 17 | 8 |
| §1.8 | 1.8.1–1.8.16 | 16 | 9 |
| §1.9 | 1.9.1–1.9.20 | 20 | 10 |
| §1.10 | 1.10.1–1.10.24 | 24 | 12 |
| §1.11 | 1.11.1–1.11.9 | 9 | 12 |
| §1.12 | 1.12.1–1.12.19 | 19 | 16 |
| §1.13 | 1.13.1–1.13.17 | 17 | 21 |
| §1.14 | 1.14.1–1.14.20 | 20 | 22 |
| §1.15 | 1.15.1–1.15.18 | 18 | 25 |
| §1.16 | 1.16.1–1.16.12 | 12 | 25 |
| §1.17 | 1.17.1–1.17.13 | 13 | 26 |
| §1.18 | 1.18.1–1.18.17 | 17 | 29 |
| §1.19 | 1.19.1–1.19.6 | 6 | 31 |
| §1.20 | 1.20.1–1.20.24 | 24 | 32 |
| §1.21 | 1.21.1–1.21.21 | 21 | 35 |
| §1.22 | 1.22.1–1.22.16 | 16 | 38 |
| §1.23 | 1.23.1–1.23.11 | 11 | 2 |
| §1.24 | 1.24.1–1.24.10 | 10 | 2 |
| §1.25 | 1.25.1–1.25.13 | 13 | 2 |
| **Part 1** | | **391** | |
| §2.1 | 2.1.1–2.1.7 | 7 | 39 |
| §2.2 | 2.2.1–2.2.25 | 25 | 13 |
| §2.3 | 2.3.1–2.3.16 | 16 | 40 |
| §2.4 | 2.4.1–2.4.24 | 24 | 44 |
| §2.5 | 2.5.1–2.5.27 | 27 | 47 |
| §2.6 | 2.6.1–2.6.23 | 23 | 33 |
| §2.7 | 2.7.1–2.7.18 | 18 | 36 |
| §2.8 | 2.8.1–2.8.14 | 14 | 17 |
| §2.9 | 2.9.1–2.9.11 | 11 | 18 |
| §2.10 | 2.10.1–2.10.14 | 14 | 49 |
| §2.11 | 2.11.1–2.11.11 | 11 | 50 |
| §2.12 | 2.12.1–2.12.11 | 11 | 51 |
| §2.13 | 2.13.1–2.13.9 | 9 | 41 |
| §2.14 | 2.14.1–2.14.12 | 12 | 42 |
| §2.15 | 2.15.1–2.15.10 | 10 | 43 |
| **Part 2** | | **232** | |
| §3.1 | 3.1.1–3.1.14 | 14 | 3 |
| §3.2 | 3.2.1–3.2.19 | 19 | 14 |
| §3.3 | 3.3.1–3.3.15 | 15 | 15 |
| §3.4 | 3.4.1–3.4.14 | 14 | 11 |
| §3.5 | 3.5.1–3.5.16 | 16 | 37 |
| §3.6 | 3.6.1–3.6.17 | 17 | 23 |
| §3.7 | 3.7.1–3.7.12 | 12 | 27 |
| §3.8 | 3.8.1–3.8.13 | 13 | 20 |
| §3.9 | 3.9.1–3.9.17 | 17 | 34 |
| §3.10 | 3.10.1–3.10.14 | 14 | 30 |
| §3.11 | 3.11.1–3.11.12 | 12 | 28 |
| §3.12 | 3.12.1–3.12.11 | 11 | 24 |
| §3.13 | 3.13.1–3.13.9 | 9 | 19 |
| §3.14 | 3.14.1–3.14.13 | 13 | 45 |
| §3.15 | 3.15.1–3.15.14 | 14 | 46 |
| §3.16 | 3.16.1–3.16.14 | 14 | 48 |
| §3.17 | 3.17.1–3.17.20 | 20 | 4 |
| §3.18 | 3.18.1–3.18.13 | 13 | 5 |
| **Part 3** | | **257** | |
| §4.1 | 4.1.1–4.1.6 | 6 | 52 |
| §4.2 | 4.2.1–4.2.6 | 6 | 52 |
| §4.3 | 4.3.1–4.3.5 | 5 | 53 |
| §4.4 | 4.4.1–4.4.10 | 10 | 53 |
| §4.5 | 4.5.1–4.5.7 | 7 | 54 |
| §4.6 | 4.6.1–4.6.9 | 9 | 54 |
| §4.7 | 4.7.1–4.7.8 | 8 | 55 |
| §4.8 | 4.8.1–4.8.10 | 10 | 56 |
| **Part 4** | | **61** | |
| §5.1 | 5.1.1–5.1.80 | 80 | 61 |
| §5.2 | 5.2.1–5.2.4 | 4 | 61 |
| §5.3 | 5.3.1–5.3.8 | 8 | 61 |
| **Part 5** | | **92** | |
| **Total** | | **1033** | |

---

## Diagram manifest

139 ids. `Type` is taken from the prompt's manifest verbatim; the full `Must show` cell for each
id lives in the source prompt at lines 2709–2874 and is pasted verbatim into the illustrator
packet for that id. `SVG file` is the canonical path — a note file that embeds this id must use
exactly this filename.

Rows with type `table` have **no SVG**: the prompt states that where the manifest's `Type` column
says `table`, a Markdown table is the correct rendering. The owning note file renders the table
in place and captions it with the same `**D-NNN** —` line.

**117 SVG + 22 table = 139.**

| Id | Title | Leaves | Type | SVG file | Owner row |
|---|---|---|---|---|---|
| D-001 | Which side of the line decides the behaviour | 1.1.2, 1.1.6 | before-after | `D-001-javac-vs-jvm.svg` | 1 |
| D-002 | The three normative documents and what each owns | 1.1.3, 1.1.4 | hierarchy | `D-002-normative-documents.svg` | 1 |
| D-003 | The release train and where 21 sits | 1.1.9, 1.1.10 | timeline | `D-003-release-train.svg` | 1 |
| D-004 | Unicode escapes are processed before tokenisation | 1.2.2 | step-sequence, 3 frames | `D-004-unicode-escape-pass.svg` | 1 |
| D-005 | Every integer and floating literal form | 1.2.5–1.2.9 | table | — | 1 |
| D-006 | The eight primitives: width, range, default | 1.3.2, 1.3.3, 1.3.19 | table | — | 6 |
| D-007 | Two's complement and the asymmetric range | 1.3.5, 1.3.21 | step-sequence, 3 frames | `D-007-twos-complement.svg` | 6 |
| D-008 | Shift distances are masked | 1.3.11, 1.3.12 | step-sequence, 3 frames | `D-008-shift-masking.svg` | 6 |
| D-009 | IEEE 754 binary64 field layout | 1.3.13, 3.15.1 | memory-layout | `D-009-ieee754-layout.svg` | 6, 46 |
| D-010 | NaN and −0.0: the three-way inconsistency | 1.3.15, 1.3.16, 2.4.5 | table | — | 6 |
| D-011 | Where each variable kind lives | 1.4.2, 1.4.3, 3.8.13 | memory-layout | `D-011-variable-storage.svg` | 16 |
| D-012 | Definite assignment as a dataflow analysis | 1.5.2–1.5.4 | flowchart | `D-012-definite-assignment.svg` | 21 |
| D-013 | Shadowing, obscuring, and hiding | 1.5.5–1.5.7 | before-after | `D-013-shadow-obscure-hide.svg` | 21 |
| D-014 | The order of instance initialisation | 1.5.11, 1.13.6 | step-sequence, 5 frames | `D-014-instance-init-order.svg` | 21 |
| D-015 | Operator precedence and associativity | 1.6.1, 1.2.14 | table | — | 7 |
| D-016 | `i = i++` on the operand stack | 1.6.4, 1.6.5 | step-sequence, 4 frames | `D-016-i-equals-i-plus-plus.svg` | 7 |
| D-017 | Compound assignment hides a narrowing cast | 1.6.6, 1.6.7 | before-after | `D-017-compound-assignment-cast.svg` | 7 |
| D-018 | The conditional operator computes its own type | 1.6.10–1.6.12 | flowchart | `D-018-ternary-typing.svg` | 7 |
| D-019 | Eleven conversions across six contexts | 1.7.1, 1.7.2 | table | — | 8 |
| D-020 | The widening ladder and its two lossy rungs | 1.7.3, 1.7.4, 3.15.13 | hierarchy | `D-020-widening-ladder.svg` | 8, 46 |
| D-021 | `int` arithmetic overflows before the widening | 1.7.10 | step-sequence, 3 frames | `D-021-int-overflow-before-widening.svg` | 8 |
| D-022 | Floating-to-integral conversion saturates | 1.7.11, 1.7.12 | table | — | 8 |
| D-023 | `switch` on a `String` is two stages | 1.8.8, 1.10.23 | step-sequence, 3 frames | `D-023-string-switch.svg` | 9 |
| D-024 | Unreachable code: `while (true)` versus `if (true)` | 1.8.16 | before-after | `D-024-unreachable-code.svg` | 9 |
| D-025 | The `IntegerCache` on the heap | 1.9.3, 1.9.7, 3.4.2 | memory-layout | `D-025-integer-cache.svg` | 10 |
| D-026 | Which wrapper caches what | 1.9.6, 3.4.5 | table | — | 10 |
| D-027 | Unboxing NPE at a line with no method call | 1.9.9, 1.9.10, 2.11.11 | step-sequence, 3 frames | `D-027-unboxing-npe.svg` | 10 |
| D-028 | `Integer` versus `int` in bulk | 1.9.19, 3.4.10, 3.4.12 | memory-layout | `D-028-integer-vs-int-bulk.svg` | 10 |
| D-029 | Inside a `String` | 1.10.2, 1.10.19, 3.2.1, 3.2.16 | memory-layout | `D-029-inside-a-string.svg` | 12 |
| D-030 | `substring`: copy since 7, shared before | 1.10.18, 3.2.17 | before-after | `D-030-substring-copy.svg` | 12 |
| D-031 | `split` is a regex, and it eats trailing empties | 1.10.13, 1.10.14 | step-sequence, 3 frames | `D-031-split-regex.svg` | 12 |
| D-032 | The string pool | 1.11.1–1.11.4, 3.2.13 | memory-layout | `D-032-string-pool.svg` | 12 |
| D-033 | Constant folding depends on `final` | 1.11.5, 1.11.6, 1.6.19 | before-after | `D-033-constant-folding-final.svg` | 12 |
| D-034 | Equal objects with unequal hashes are unreachable | 1.12.3, 1.12.4, 3.13.4 | step-sequence, 3 frames | `D-034-equal-unequal-hash.svg` | 16 |
| D-035 | `getClass()` versus `instanceof` in `equals` | 1.12.7 | before-after | `D-035-getclass-vs-instanceof.svg` | 16 |
| D-036 | `clone()` is shallow | 1.12.12, 2.8.1, 2.8.7 | before-after | `D-036-clone-is-shallow.svg` | 16 |
| D-037 | `finalize` versus `Cleaner` versus `AutoCloseable` | 1.12.15–1.12.17, 2.9.4, 2.9.11 | timeline | `D-037-finalize-cleaner-autocloseable.svg` | 16 |
| D-038 | The full initialization order of a `new` | 1.13.6, 1.13.7 | step-sequence, 6 frames | `D-038-new-init-order.svg` | 21 |
| D-039 | What triggers class initialization | 1.13.9, 1.13.10, 3.6.5, 3.6.6 | decision-tree | `D-039-class-init-triggers.svg` | 21 |
| D-040 | `ExceptionInInitializerError`, then silence | 1.13.13, 3.6.10 | timeline | `D-040-exception-in-initializer.svg` | 21 |
| D-041 | Access modifier visibility | 1.14.12, 1.14.13 | table | — | 22 |
| D-042 | A `static final` constant is copied into every caller | 1.14.7, 3.12.1, 3.12.3 | before-after | `D-042-constant-inlining.svg` | 22 |
| D-043 | Overload resolution in three phases | 1.15.6–1.15.8 | flowchart | `D-043-overload-resolution.svg` | 25 |
| D-044 | Static hiding versus instance overriding | 1.14.2, 1.15.5 | before-after | `D-044-static-hiding.svg` | 25 |
| D-045 | Fields are not polymorphic | 1.15.12, 3.7.9 | memory-layout | `D-045-fields-not-polymorphic.svg` | 25 |
| D-046 | The fragile base class | 1.15.15 | step-sequence, 3 frames | `D-046-fragile-base-class.svg` | 25 |
| D-047 | Interface versus abstract class | 1.16.1, 1.16.11 | table | — | 25 |
| D-048 | Diamond resolution for default methods | 1.16.5, 1.16.6 | hierarchy | `D-048-default-method-diamond.svg` | 25 |
| D-049 | The four nested-class kinds | 1.17.1, 1.17.13 | table | — | 26 |
| D-050 | `this$0` keeps the whole enclosing object alive | 1.17.8, 3.11.2, 3.11.7 | memory-layout | `D-050-this0-retention.svg` | 26 |
| D-051 | `this` in a lambda versus an anonymous class | 1.17.9 | before-after | `D-051-this-lambda-vs-anon.svg` | 26 |
| D-052 | `values()` clones on every call | 1.18.7, 3.10.2 | step-sequence, 3 frames | `D-052-values-clone.svg` | 29 |
| D-053 | The `Throwable` hierarchy | 1.20.1, 1.20.4–1.20.6 | hierarchy | `D-053-throwable-hierarchy.svg` | 32 |
| D-054 | try-with-resources: close order and suppression | 1.20.12, 1.20.14, 1.20.15 | step-sequence, 4 frames | `D-054-twr-suppression.svg` | 32 |
| D-055 | `return` inside `finally` swallows everything | 1.20.16, 3.9.3 | before-after | `D-055-return-in-finally.svg` | 32 |
| D-056 | Generics are invariant; arrays are covariant | 1.21.9, 1.21.10, 1.22.5 | before-after | `D-056-invariant-vs-covariant.svg` | 35 |
| D-057 | PECS on a real signature | 1.21.11–1.21.14, 2.7.3 | flowchart | `D-057-pecs.svg` | 35 |
| D-058 | An array in memory | 1.22.11, 3.8.4 | memory-layout | `D-058-array-in-memory.svg` | 38 |
| D-059 | Varargs allocate an array per call | 1.22.14, 1.22.15 | step-sequence, 3 frames | `D-059-varargs-allocation.svg` | 38 |
| D-060 | Module strong encapsulation | 1.23.6–1.23.8 | flowchart | `D-060-module-encapsulation.svg` | 2 |
| D-061 | Retention decides who can see an annotation | 1.24.3, 1.24.4, 1.24.10 | timeline | `D-061-annotation-retention.svg` | 2 |
| D-062 | `nanoTime` versus `currentTimeMillis` | 1.25.5, 2.5.26 | timeline | `D-062-nanotime-vs-millis.svg` | 2 |
| D-063 | `Math.round`, `floor`, `ceil`, `rint`, truncation | 1.25.7, 1.3.8, 1.3.7 | table | — | 2 |
| D-064 | The master cost table | 2.1.1 | table | — | 39 |
| D-065 | Concatenation in a loop is quadratic | 2.2.1, 3.3.14 | cost-curve | `D-065-concat-quadratic.svg` | 13 |
| D-066 | `StringBuilder` growth is `2 × old + 2` | 2.2.3, 3.3.3, 3.3.7 | cost-curve | `D-066-stringbuilder-growth.svg` | 13 |
| D-067 | Code unit, code point, grapheme cluster | 2.2.20, 2.2.21, 1.3.4 | memory-layout | `D-067-code-unit-point-grapheme.svg` | 13 |
| D-068 | Where encoding actually happens | 2.2.17–2.2.19 | before-after | `D-068-where-encoding-happens.svg` | 13 |
| D-069 | The five immutability rules | 2.3.1–2.3.5, 2.3.9 | flowchart | `D-069-immutability-rules.svg` | 40 |
| D-070 | Defensive copy ordering and the TOCTOU window | 2.3.3 | step-sequence, 3 frames | `D-070-defensive-copy-toctou.svg` | 40 |
| D-071 | Why `double` cannot hold 0.1 | 2.4.1, 2.4.2, 3.15.2 | step-sequence, 3 frames | `D-071-double-cannot-hold-01.svg` | 44 |
| D-072 | `BigDecimal` is an unscaled integer plus a scale | 2.4.7, 3.14.1, 3.14.2 | memory-layout | `D-072-bigdecimal-structure.svg` | 44 |
| D-073 | `equals` sees scale; `compareTo` does not | 2.4.11, 2.4.12, 3.14.7, 3.14.8 | before-after | `D-073-bigdecimal-equals-vs-compareto.svg` | 44 |
| D-074 | `HALF_UP` versus `HALF_EVEN` over a million roundings | 2.4.14 | cost-curve | `D-074-half-up-vs-half-even.svg` | 44 |
| D-075 | The `java.time` type map | 2.5.4, 2.5.7 | hierarchy | `D-075-java-time-type-map.svg` | 47 |
| D-076 | Three types, three questions | 2.5.5, 2.5.6, 2.5.11 | table | — | 47 |
| D-077 | The DST gap and the DST overlap | 2.5.9, 2.5.10, 3.16.5 | timeline | `D-077-dst-gap-and-overlap.svg` | 47 |
| D-078 | `Duration.ofDays(1)` versus `Period.ofDays(1)` | 2.5.8 | before-after | `D-078-duration-vs-period.svg` | 47 |
| D-079 | End-of-month clamping | 2.5.14 | step-sequence, 3 frames | `D-079-end-of-month-clamping.svg` | 47 |
| D-080 | The `SimpleDateFormat` race | 2.5.2, 2.4.24 | timeline | `D-080-simpledateformat-race.svg` | 47 |
| D-081 | Checked or unchecked | 2.6.1, 2.6.2, 2.6.8 | decision-tree | `D-081-checked-or-unchecked.svg` | 33 |
| D-082 | Exception translation preserves the cause | 2.6.6, 1.20.8, 3.9.13 | step-sequence, 3 frames | `D-082-exception-translation.svg` | 33 |
| D-083 | The reference strength ladder | 2.9.2, 2.9.3 | hierarchy | `D-083-reference-strength-ladder.svg` | 18 |
| D-084 | The `Cleaner` capture trap | 2.9.4 | before-after | `D-084-cleaner-capture-trap.svg` | 18 |
| D-085 | `readObject` is a constructor that skips your validation | 2.10.5, 2.10.6 | step-sequence, 3 frames | `D-085-readobject-bypasses-validation.svg` | 49 |
| D-086 | `orElse` evaluates eagerly | 2.11.4 | before-after | `D-086-orelse-eager.svg` | 50 |
| D-087 | `getX` versus `getDeclaredX` | 2.12.2, 2.12.3 | table | — | 51 |
| D-088 | Pass-by-value: mutate, reassign, swap | 2.13.1–2.13.3, 2.13.5 | step-sequence, 4 frames | `D-088-pass-by-value.svg` | 41 |
| D-089 | Which construct do I reach for | 2.15.1–2.15.10 | decision-tree | `D-089-which-construct.svg` | 43 |
| D-090 | The `javac` pipeline | 3.1.1, 3.1.12 | flowchart | `D-090-javac-pipeline.svg` | 3 |
| D-091 | Inside a class file | 3.1.2, 3.1.3, 3.1.5 | memory-layout | `D-091-inside-a-class-file.svg` | 3 |
| D-092 | The desugaring catalogue | 3.1.6, 3.1.7 | table | — | 3 |
| D-093 | Compact strings: one byte per Latin-1 character | 3.2.2–3.2.5 | before-after | `D-093-compact-strings.svg` | 14 |
| D-094 | `String.hashCode` and the `hashIsZero` flag | 3.2.6, 3.2.7, 1.10.19 | step-sequence, 3 frames | `D-094-string-hashcode.svg` | 14 |
| D-095 | Two different strings, one hash | 3.2.8, 3.13.9 | step-sequence, 2 frames | `D-095-string-hash-collision.svg` | 14 |
| D-096 | `String.equals`, line by line | 3.2.9, 3.2.10, 1.10.20 | flowchart | `D-096-string-equals.svg` | 14 |
| D-097 | The StringTable and `intern()` | 3.2.11, 3.2.12, 1.11.7 | memory-layout | `D-097-stringtable-intern.svg` | 14 |
| D-098 | Deduplication is not interning | 3.2.14, 3.2.15, 1.11.8 | before-after | `D-098-dedup-vs-intern.svg` | 14 |
| D-099 | `newCapacity` and the coder shift | 3.3.3–3.3.5 | step-sequence, 3 frames | `D-099-newcapacity-coder-shift.svg` | 15 |
| D-100 | `+` before and after Java 9 | 3.3.9–3.3.11, 2.2.2 | before-after | `D-100-concat-before-after-9.svg` | 15 |
| D-101 | Indified concat does not fix the loop | 3.3.14, 2.2.1 | step-sequence, 3 frames | `D-101-indy-concat-loop.svg` | 15 |
| D-102 | Three ways `IntegerCache` gets filled | 3.4.1–3.4.4, 1.9.4, 1.9.5 | flowchart | `D-102-integercache-fill-paths.svg` | 11 |
| D-103 | Escape analysis erases a box | 3.4.8, 3.4.9, 2.1.2 | before-after | `D-103-escape-analysis-box.svg` | 11 |
| D-104 | What erasure emits | 3.5.1, 3.5.2, 1.21.7 | before-after | `D-104-what-erasure-emits.svg` | 37 |
| D-105 | Why a bridge method exists, and how it throws | 3.5.3–3.5.6 | step-sequence, 3 frames | `D-105-bridge-method.svg` | 37 |
| D-106 | Heap pollution through generic varargs | 3.5.9, 3.5.10, 1.21.18 | step-sequence, 4 frames | `D-106-heap-pollution.svg` | 37 |
| D-107 | Loading, linking, initialization | 3.6.1–3.6.4 | step-sequence, 3 frames | `D-107-load-link-init.svg` | 23 |
| D-108 | The class-initialization state machine and its deadlock | 3.6.7–3.6.9, 1.13.12 | state-transition | `D-108-class-init-state-machine.svg` | 23 |
| D-109 | The five invoke instructions | 3.7.1–3.7.3, 1.15.10 | table | — | 27 |
| D-110 | vtable and itable | 3.7.4, 3.7.5, 1.15.9 | memory-layout | `D-110-vtable-itable.svg` | 27 |
| D-111 | Monomorphic, bimorphic, megamorphic | 3.7.6, 3.7.7, 1.15.11 | state-transition | `D-111-inline-caches.svg` | 27 |
| D-112 | The object header and field reordering | 3.8.1, 3.8.2, 3.8.5, 3.8.7, 3.8.9 | memory-layout | `D-112-object-header-layout.svg` | 20 |
| D-113 | The exception table costs nothing to enter | 3.9.1, 3.9.2, 3.9.5 | memory-layout | `D-113-exception-table.svg` | 34 |
| D-114 | `finally` is duplicated into every exit path | 3.9.3, 3.9.4, 1.20.16 | before-after | `D-114-finally-duplication.svg` | 34 |
| D-115 | `fillInStackTrace` dominates exception cost | 3.9.6–3.9.8, 3.9.15 | cost-curve | `D-115-fillinstacktrace-cost.svg` | 34 |
| D-116 | Why a production NPE has no stack trace | 3.9.9, 2.6.13 | timeline | `D-116-fast-throw-no-trace.svg` | 34 |
| D-117 | What `javac` generates for an enum | 3.10.1, 3.10.4–3.10.6 | before-after | `D-117-generated-enum.svg` | 30 |
| D-118 | `$SwitchMap` and why it exists | 3.10.9, 1.8.9 | step-sequence, 3 frames | `D-118-switchmap.svg` | 30 |
| D-119 | `EnumSet` as a bit vector, `EnumMap` as an array | 3.10.10–3.10.12, 1.18.11 | memory-layout | `D-119-enumset-enummap.svg` | 30 |
| D-120 | `this$0` and `val$x` in the class file | 3.11.2, 3.11.3, 1.17.10 | before-after | `D-120-this0-valx.svg` | 28 |
| D-121 | `access$000` bridges versus nestmates | 3.11.4–3.11.6 | before-after | `D-121-access-bridges-vs-nestmates.svg` | 28 |
| D-122 | The `final` field freeze | 3.12.4, 3.12.5, 2.3.13 | timeline | `D-122-final-field-freeze.svg` | 24 |
| D-123 | `static final` is trusted; instance `final` is not | 3.12.1, 3.12.6, 3.12.7, 3.12.11 | table | — | 24 |
| D-124 | The identity hash lives in the mark word | 3.13.1–3.13.3, 1.12.11 | step-sequence, 3 frames | `D-124-identity-hash-mark-word.svg` | 19 |
| D-125 | `intCompact` versus `intVal` | 3.14.2–3.14.4 | before-after | `D-125-intcompact-vs-intval.svg` | 45 |
| D-126 | `Math.ulp` and the spacing of doubles | 3.15.6, 3.15.4, 2.4.4 | cost-curve | `D-126-math-ulp-spacing.svg` | 46 |
| D-127 | The `java.time` field layouts | 3.16.1–3.16.4 | memory-layout | `D-127-java-time-field-layouts.svg` | 48 |
| D-128 | `ZoneRules` resolves gaps and overlaps | 3.16.5, 3.16.6, 2.5.13 | step-sequence, 3 frames | `D-128-zonerules.svg` | 48 |
| D-129 | What changed in which release | 3.17.1–3.17.20, 5.2.2 | table | — | 4 |
| D-130 | `MyString` field layout versus `java.lang.String` | 4.1.1, 4.1.5, 4.1.6 | before-after | `D-130-mystring-layout.svg` | 52 |
| D-131 | `MyStringBuilder` growth trace | 4.2.1, 4.2.4, 4.2.5 | cost-curve | `D-131-mystringbuilder-growth.svg` | 52 |
| D-132 | `MyInteger` cache boundary | 4.3.1, 4.3.2, 4.3.4 | before-after | `D-132-myinteger-cache-boundary.svg` | 53 |
| D-133 | `Result<T,E>` versus a checked exception | 4.4.2, 2.6.3 | flowchart | `D-133-result-vs-checked.svg` | 53 |
| D-134 | The enum state machine and its `EnumMap` transition table | 4.5.4 | state-transition | `D-134-bonus-state-machine.svg` | 54 |
| D-135 | `Money` two ways | 4.7.1–4.7.3, 2.4.18 | before-after | `D-135-money-two-ways.svg` | 55 |
| D-136 | The trap index | 5.2.1 | table | — | 61 |
| D-137 | The version-stale claims table | 5.2.2 | table | — | 61 |
| D-138 | The five most expensive real-world mistakes | 5.2.3 | table | — | 61 |
| D-139 | The numbers drill card | 5.3.1 | table | — | 61 |

### Substitutions

None recorded. This block records any `D-NNN` an illustrator reports as not renderable as a
picture; the owning file then renders a Markdown table at that point instead of an embed, and the
reason is logged here. Recorded **before** the writer pass, so no writer ever discovers a missing
SVG at write time.

---

## Naming and cross-file notes

Slugs that no longer describe their contents. Left frozen deliberately — every inbound
link and nav label is correct, so renaming would churn links for a cosmetic gain.

| File | Note |
|---|---|
| `objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md` | Slug predates its retitle; it holds the `equals`/`hashCode` contracts only. The remaining `Object` methods are in `01c-object-methods.md`. |
| `build-it/05c-dispatch-and-value-harnesses.md` | Holds the pass-by-value harness only; the overload-resolution material moved to `05j-overload-resolution-harness.md`. Neighbours link via the nav label "The pass-by-value harness". |

Cross-file measurement disagreement — **resolved**:

`exceptions/03b-internals-stack-trace-capture.md` originally concluded that the harness
never observes a normal-versus-stackless construction ratio near 10× "at any depth", and
built a pitfall and a self-test answer on it. That was contradicted by the file's own
depth-1 row — `normal=237.0ns stackless-ctor=4.8ns`, a **49.4×** ratio it never computed —
so the universal quantifier had been attached to a band drawn from the depth-100 and
depth-1000 rows only. Its data was sound; its conclusion was not.

`build-it/03h-stackless-exception.md` independently measures **11.15× at depth 1** and
**1.47× at depth 100**, the latter within 4% of `03b`'s own depth-100 figures — two
separately written harnesses converging, which is what made the depth-1 contradiction
unambiguous rather than arguable. The ratio genuinely collapses with depth: capture costs
~15 ns/frame, unwind ~36.5 ns/frame, and a stackless exception removes only the first, so
by depth 500 the unwind (~18,248 ns) swamps the capture (~7,496 ns).

The 11× versus 49× gap at depth 1 is a property of the exception, not the harness:
`03h`'s type builds a four-entry immutable context map costing **25.02 ns**, against a
literal-carrying stackless type at 4.8 ns and a preallocated no-context singleton at
2.13 ns. At depth 1, structured context is essentially the whole cost of a stackless
exception — the more useful lesson than either ratio.

Both files now state depth beside every ratio and cross-reference each other. `03b` carries
a depth-ratio table computing the depth-1 case, and its pitfall warns against quoting any
single ratio in either direction. `exceptions/03c-internals-fast-throw-and-truncation.md`'s
1.4–1.5× figure is correct as written — it is explicitly a realistic-depth figure.

---

## Superseded files present on disk

These three files are **not** in the file plan above and are **not** deliverables. They are
pre-split originals that survived a race: a "stop splitting" instruction arrived after their
replacement splits had already been dispatched, so both generations exist. Their leaf ranges are
fully covered by the replacements listed in the file plan, so **every leaf in the plan is still
covered exactly once by plan files**. Retained pending review rather than deleted.

| File on disk | Lines | Leaves it duplicated | Superseded by |
|---|---|---|---|
| `control-flow/01b-assertions-and-unreachable-code.md` | 617 | 1.8.13–1.8.16 | rows 9d, 9e |
| `primitives-and-conversions/02a-assignment-bitwise-and-comparison.md` | 599 | 1.6.6–1.6.9, 1.6.14–1.6.15 | rows 7a, 7b |
| `primitives-and-conversions/02b-conditional-and-string-concatenation.md` | 574 | 1.6.10–1.6.13, 1.6.16–1.6.18 | rows 7c, 7d |

Consequence to be aware of: `control-flow/` currently holds two files whose names begin `01b-`
(`01b-assertions-and-unreachable-code.md`, superseded, and `01b-string-and-enum-switch.md`,
row 9b), so directory sort order between them is ambiguous. Resolved by removing the superseded
file, or by renaming it out of the `01b-` slot.

---

## Resolved research items

The prompt flags three claims as unverified and forbids printing a number for any of them
without confirmation. All three were resolved before the writer pass.

| Claim | Leaf | Resolution |
|---|---|---|
| `-XX:StringTableSize` default | 3.2.11 | **65536**, confirmed. `java -XX:+PrintFlagsFinal -version` on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64: `uintx StringTableSize = 65536 {product} {default}` |
| `-XX:MaxJavaStackTraceDepth` default | 3.9.10 | **1024**, confirmed. Same run: `intx MaxJavaStackTraceDepth = 1024 {product} {default}` |
| *Effective Java* item-number mapping | 2.14.11 | Full 1–90 item list corroborated against two independent published tables of contents, not against the physical book. Writers cite **both number and title** ("Item 17: *Minimize mutability*") so a wrong number is self-correcting |

Other flag defaults confirmed in the same run and available to every writer:
`AutoBoxCacheMax = 128`, `StringDeduplicationAgeThreshold = 3`, `ObjectAlignmentInBytes = 8`,
`OmitStackTraceInFastThrow = true`, `CompactStrings = true`, `UseCompressedOops = true`
(ergonomic). `UseCompactObjectHeaders` does not exist on JDK 21.

---

## Open questions

None yet. Writers append `**Unverified:**` claims here as their envelopes return.

---

## Deferred

None. Every one of the 1033 enumerated leaves is assigned to exactly one file above.
