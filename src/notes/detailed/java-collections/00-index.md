# 02 Java Collections — detailed note set: file plan and status

**Topic:** Java Collections (topic 02)
**Target version:** Java 21 LTS
**Source prompt:** `src/metadata/prompts/02-java-collections-prompt.md`
**Prompt SHA-256:** `f35397ec4950edd60b817af35538620b4a2a3d516fbfe8deb51f48d4f827f48a`
**Prompt last modified:** 2026-08-22 21:43:40 (188,979 bytes)
**Total syllabus leaves:** 901
**Total manifest diagrams:** 152 (D-01 … D-152), of which 8 are `table`-type and render as Markdown tables, 144 as standalone SVG

On resume: if the prompt hash no longer matches the value above, every row in the file plan
reverts to `planned` and the set is rebuilt. The verbatim diagram manifest (id, type,
must-show contents) lives in [`00-diagram-manifest.md`](00-diagram-manifest.md) so that a
resumed run never needs the prompt to know what a `D-NN` depicts.

## Layout

Subject-major, per this agent's folder law, which overrides the prompt's tier-major
`# OUTPUT CONTRACT` path list. The prompt's **content assignments** — which sections and
leaves travel together — are preserved and re-mapped onto subject folders.

```
java-collections/
├── 00-index.md                  <- this file
├── 00-diagram-manifest.md       <- verbatim D-NN manifest
├── framework/                   <- §1.1–1.4, §1.10, §2.14, §2.15, §3.16, §3.18
├── contracts/                   <- §1.6, §1.7, §1.8, §2.5
├── iteration/                   <- §1.5, §2.2, §3.13
├── sequenced-collections/       <- §1.9
├── cost-and-memory/             <- §2.1, §3.15, §3.17
├── array-list/                  <- §3.1, §3.2, §4.1
├── linked-list/                 <- §3.3, §4.2
├── array-deque/                 <- §3.4, §4.4
├── priority-queue/              <- §3.5, §4.5
├── hash-map/                    <- §3.6, §4.3
├── linked-hash-map/             <- §3.7, §4.6.2–4.6.3
├── tree-map/                    <- §2.10, §3.8, §4.6.1
├── sets/                        <- §2.9.17–2.9.20, §2.12, §3.9
├── specialised-maps/            <- §2.9.1–2.9.16, §3.10, §3.11
├── immutable-collections/       <- §2.3, §2.4, §3.12
├── concurrent-collections/      <- §3.14, §4.6.8
├── utilities/                   <- §2.6, §2.7, §2.8, §2.11, §2.13, §2.16, §2.17
├── build-it/                    <- §4.6 remainder
├── 90-interview-basics.md       <- BASICS tier, all subjects
├── 91-interview-intermediate.md <- INTERMEDIATE tier, all subjects
├── 92-interview-internals.md    <- INTERNALS tier, ends with the atomic concept checklist
├── 93-drills-and-traps.md       <- §5.2 trap index, §5.3 drills
└── diagrams/                    <- flat, topic-scoped, D-NN-slug.svg
```

**18 subject folders.** Per-tier interview Q&A count is therefore `10 + 2 × (18 − 5) = 36`
per interview file, plus 5 predict-the-output puzzles per file.

**Nav rule:** the file plan table below is in plan order. Each file's `Previous` is the row
above it and its `Next` is the row below it. Row 1 omits `Previous:`; the last row omits
`Next:`. Subject-folder files reach diagrams with `../diagrams/D-NN-slug.svg`; the root
`90`–`93` files use `diagrams/D-NN-slug.svg`.

## Folds recorded

- **§2.7 (`Arrays` utility surface, 6 leaves)** is folded into
  `utilities/01-collections-and-arrays.md` rather than getting its own file: at 6 leaves,
  four of which cross-reference §2.3 and §2.8, it cannot carry a basics/cost/internals arc
  and would land under the 120-line content floor.
- **§2.14 (choosing, 10 leaves)** is folded into `framework/06-matrices-and-choosing.md`
  with §1.10: the decision tree and the three matrices are the same artefact read two ways.
- **§2.15 (legacy, 9 leaves)** was originally folded with §3.16 into a single
  `framework/07-legacy-and-version-history.md`. **Fold reversed on 2026-08-26:** the combined
  file came back at 695 lines, past the 600-line hard split. §2.15 and §3.16 are now
  `framework/07-legacy-a-vector-stack-hashtable.md` (rows 7a) and
  `framework/07-legacy-b-version-history.md` (row 7b). The cross-reference between them stands
  in prose — "why `Vector` still exists" opens 7a and closes 7b — but they are two files.
- **§3.14.34–3.14.37** are folded into
  `concurrent-collections/05-blocking-and-lock-free-queues.md`: 3 leaves alone is a stub.
  **Amended 2026-08-28 by the row-57–61 pre-split below:** 3.14.34, 3.14.35 and 3.14.37 land in
  row 61b (`05b-lock-free-queues-and-choosing.md`), 3.14.36 in row 60b. The fold stands — none of
  them got its own file — but the parent is now the 61/61b pair, not a single row 61.
- **Rows 58–61 pre-split TWO ways each on 2026-08-28, before dispatch, per the item-27 policy and
  the §3.6/§3.8 precedent.** §3.14's 31 leaves in rows 58–61 are the densest `[SOURCE]`/`[PROVE]`
  block left in the set: `ConcurrentHashMap.java` is 6,385 lines, `transfer` alone is ~130,
  and every quoted line must then be explained. Four 470-line estimates for 8/9/5/10 leaves is the
  same mis-pricing that turned §3.6's five rows into fourteen files, so the split is planned here
  rather than discovered at 1,300 lines. Every cut is at a leaf boundary and at a concept boundary:
  - row 58 → `02-internals-chm-a.md` (3.14.7–3.14.12: fields, `sizeCtl`, `spread`, special hashes,
    the write path, lock-free `get`) and `02b-internals-chm-a2-cooperative-resize.md` (3.14.13,
    3.14.14: `transfer`, `ForwardingNode`, `helpTransfer`). The seam is steady-state versus resize.
  - row 59 → `03-internals-chm-b.md` (3.14.15–3.14.19: counters, `@Contended`, `TreeBin`, the
    compound methods, the deadlock) and `03b-internals-chm-c-bulk-nulls-and-segments.md`
    (3.14.20–3.14.23: bulk ops, `newKeySet`, no nulls, Java 7 segments).
  - row 60 → `04-copy-on-write.md` (3.14.24–3.14.26, the JDK class) and
    `04b-build-copy-on-write-by-hand.md` (3.14.36 + 4.6.8, the build-it). Splitting the build-it
    off is the §4.1/§4.3/§4.5 precedent: a working class plus its pinned harness never shares a
    file with a source walk.
  - row 61 → `05-blocking-and-lock-free-queues.md` (3.14.27–3.14.30, the blocking family) and
    `05b-lock-free-queues-and-choosing.md` (3.14.31–3.14.35, 3.14.37, the lock-free family plus the
    failure catalogue and the choosing table). The seam is blocking versus lock-free.
  **One diagram is reassigned, deliberately.** The manifest and the pre-split file plan both put
  **D-129 (`sizeCtl` states) in row 59**, but its only leaf, **3.14.8, lives in row 58**. D-129 moves
  to row 58 so the picture sits at the point of explanation; row 59 keeps D-130 and row 59b takes
  D-131. Frame series: D-128 → D-128a/b/c/d and D-136 → D-136a/b/c/d, one file per frame per the
  diagram spec, not manifest substitutions — every id lands.
  Nav chain: `immutable-collections/04c` → `01` → `02` → `02b` → `03` → `03b` → `04` → `04b` →
  `05` → `05b` → `05c` → `../utilities/01-collections-and-arrays.md`.
- **Row 61b split again on 2026-08-28: `05b-lock-free-queues-and-choosing.md` came back at 965
  lines**, 165 past the 800-line hard cap, even after the row-61 two-way pre-split above. Six
  leaves, three of them full source walks, was too much for one file. Split at the concept boundary
  between **mechanism and synthesis**: `05b-lock-free-queues-and-choosing.md` (row 61b, 3.14.31–
  3.14.33 — `ConcurrentLinkedQueue`, `LinkedTransferQueue`, `ConcurrentSkipListMap`, keeping all
  four D-136 frames and all three source walks whole) and
  `05c-failure-catalogue-and-choosing.md` (row 61c, 3.14.34/3.14.35/3.14.37 — the failure
  catalogue, the choosing table, virtual threads). **`05b`'s filename is deliberately stale** —
  "and-choosing" now describes `05c` — and must NOT be renamed, per the precedent already set by
  `hash-map/03b`, `linked-hash-map/01b`/`01c` and `specialised-maps/03`: renaming orphans a written
  file, and a cosmetically stale filename is the cheaper defect. Both titles, footers and leaf
  lists correctly claim only their real leaves. The split was a redistribution, not a trim — no
  concept was dropped and no source walk shortened.
- **Row 60b (§3.14.36, §4.6.8, `CopyOnWriteList` over `AtomicReference<Object[]>`) — HARNESS PIN
  (item 28), and the md5 INDEPENDENTLY REPRODUCED by the orchestrator on 2026-08-28** from a clean
  extract-compile-run against the shipped page, rather than taken on the writer's report.
  - *Inclusion rule, purely mechanical:* a fence must be tagged `java` **and** its first line must
    full-match `// (\w+\.java)`. No inference from content; nothing excluded is ever repaired,
    wrapped or spliced to make it compile.
  - *Included:* **4 labelled blocks, one per label, 373 lines** — `CopyOnWriteList.java` 179,
    `Demo.java` 126, `AtomicListRef.java` 35, `BrokenCopyOnWriteList.java` 33. Every one is a
    **whole compilation unit**, so **no splicing** and **no cross-block ordering question arises** —
    unlike §4.3 and §4.1, where block order was load-bearing. `BrokenCopyOnWriteList` is a
    deliberate counter-example that **is in the build**: it compiles, runs, and contributes to the
    digest, because `Demo` instantiates it to print the lost update.
  - *Excluded:* **2 `java` blocks** lacking the label (the two `## Pitfalls` "Wrong" blocks —
    `addWrong`, and the `getAndUpdate` side-effect snippet opening `int[] attempts = {0};`), plus
    **1 untagged fence**. **Correction to the writer's report, which said "0 untagged fences":**
    there is one — the `javac`/`java`/`md5` command block inside its own `## Build proof` section.
    The writer's substantive claim is still right, and is the reason the count is only one: this
    file quotes **no JDK source in a fence at all** (the `lock`-field fact is cited inline in prose
    with a file:line reference), so no source quote could reach the extractor even in principle.
  - *Wrapping:* **none in the harness.** Both intentionally-throwing calls in `Demo`
    (`list.get(5)`, `list.iterator().remove()`) are inside `try`/`catch` **in the published code**,
    so the digest is over unmodified page content and item 29 is satisfied in the notes rather than
    in the harness. The JVM exits 0 and no stream is truncated.
  - *Commands:* `javac -d out CopyOnWriteList.java AtomicListRef.java BrokenCopyOnWriteList.java
    Demo.java` → zero errors; then `java -cp out Demo > run.out 2>&1`; then BSD `md5 run.out` (not
    `md5sum`). JDK `/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home`, build
    21.0.7+8-LTS-245, Apple M4 Pro arm64.
  - *Coverage:* **stdout and stderr merged (`2>&1`)**, one `java Demo` invocation, **9 deterministic
    lines**. Deterministic because the two caught exceptions throw at fixed call sites, the CAS-retry
    and lost-update proofs are **hand-sequenced on one thread with no real concurrency**, and the
    8-thread × 500-element correctness check prints only a pass/fail summary from an assertion that
    holds regardless of interleaving. **No timing or wall-clock value is printed anywhere**, which is
    what makes the digest reproducible at all.
  - *Digest:* **`1ef5f083139dd90dd5f6b9446f17bb6b`.** Three runs agree: the writer's original build,
    its own re-extraction, and the orchestrator's independent rebuild in `/tmp/jc-row60b-verify/`,
    whose block classification was re-derived from the published page alone and matched the writer's
    per-label counts exactly. Compiled classes left on disk at `/tmp/jc-row60b-verify/out/`.
- **Row 7a is NOT split.** An entry here previously recorded a split of
  `framework/07-legacy-a-vector-stack-hashtable.md` into `07-legacy-a1-vector-and-stack.md`
  and `07-legacy-a2-hashtable-and-enumeration.md`, justified by a writer returning `blocked`
  at 653 lines. That writer belonged to a different session working the same plan; the file
  in this lane was 401 lines and needed no split. Entry removed 2026-08-26. Those two `a1`/`a2`
  paths must never be created. Nav chain is `06` → `07-legacy-a` → `07-legacy-b` → `08`.
- **Row 23 split on 2026-08-26.** `array-list/02-internals-b-mutation.md` came back at 878 lines, past the 600-line hard split; §3.1.22–3.1.23 (bulk removal) is now `array-list/02b-internals-bulk-removal.md` (row 23b), leaving §3.1.11–3.1.21 in row 23. Nav chain is `02-internals-b-mutation` → `02b-internals-bulk-removal` → `03-internals-c-views-and-iterators`.

- **Row 30 split on 2026-08-27.** §4.4's 8 leaves did not fit one file: 4.4.1/4.4.2/4.4.3/4.4.5/4.4.6 stay in `array-deque/02-build-my-array-deque.md` (row 30, 600) and 4.4.4/4.4.7/4.4.8 move to `array-deque/03-build-my-array-deque-b-grow-iterator-and-diff.md` (row 30b, 464). Split verified behaviour-preserving: the 10 code blocks labelled `// MyArrayDeque.java` extracted in 02→03 order, plus the single `// PowerOfTwoDeque.java` block, compile clean under JDK 21.0.7 `-Xlint:all` and produce demo output md5 `122358ab70fd66312ade569ffefd4cdc`, byte-identical to the pre-split single-file build. Nav chain: `01-internals` -> `02-build-my-array-deque` -> `03-build-my-array-deque-b-grow-iterator-and-diff` -> `priority-queue/01-internals-a-heap`.

- **Row 31 split on 2026-08-27.** `priority-queue/01-internals-a-heap.md` came back at 683 lines, past the 600-line hard split. §3.5.11–3.5.13 (`removeAt`, `forgetMeNot`, and the unsorted-iteration facts) is now `priority-queue/01b-internals-removeat-and-iteration.md` (row 31b, 377), leaving §3.5.1–3.5.10 in row 31 (563). The split point is a concept boundary: the four sift/heapify concepts close in row 31, and `removeAt` opens 31b. **D-84 moved with its leaf** — the manifest assigns D-84 to leaf 3.5.11, which row 32 previously listed; row 32 now carries no diagram, which is correct since none of §3.5.14–3.5.20 has a manifest entry. Nav chain: `01-internals-a-heap` -> `01b-internals-removeat-and-iteration` -> `02-internals-b-traps`.

- **Row 33 split THREE ways on 2026-08-27**, per the §4.1 build-it precedent. §4.5's 9 leaves are three working classes plus a diff table against a 440-line estimate. Leaves 4.5.1/4.5.2/4.5.4/4.5.5 stay in `priority-queue/03-build-my-priority-queue.md` (row 33, 525); 4.5.3/4.5.6 move to `priority-queue/04-build-my-priority-queue-b-operations-and-iterator.md` (row 33b, 479); 4.5.7/4.5.8/4.5.9 move to `priority-queue/05-build-my-priority-queue-c-variants-and-diff.md` (row 33c, 437). Split verified behaviour-preserving: the 10 code blocks labelled `// MyPriorityQueue.java` extracted in 03→04→05 order, plus the single `// StablePriorityQueue.java` and single `// BoundedTopK.java` blocks, compile clean under JDK 21.0.7 `-Xlint:all` and produce demo output md5 `dd0aac2a82b60fbaec484200d437e638`, byte-identical to the pre-split single-file build. Nav chain: `02-internals-b-traps` -> `03-build-my-priority-queue` -> `04-build-my-priority-queue-b-operations-and-iterator` -> `05-build-my-priority-queue-c-variants-and-diff` -> `hash-map/01-internals-a-constants-and-hash`.

- **Row 28 split on 2026-08-27.** §4.2's 8 leaves did not fit one file: 4.2.1–4.2.4 stay in
  `linked-list/02-build-my-linked-list.md` (row 28) and 4.2.5–4.2.8 move to
  `linked-list/03-build-my-linked-list-b-iterators-and-benchmark.md` (row 28b). Nav chain:
  `01-internals` -> `02-build-my-linked-list` -> `03-build-my-linked-list-b-iterators-and-benchmark`
  -> `array-deque/01-internals`.

- **§4.2 (row 28) split two ways on 2026-08-27**, pre-split at planning time rather than after an
  overrun, per the §4.1 pattern below. `linked-list/02-build-my-linked-list.md` (row 28) carries
  4.2.1–4.2.4 at 600 lines; `linked-list/03-build-my-linked-list-b-iterators-and-benchmark.md`
  (row 28b) carries 4.2.5–4.2.8 at 497. Split verified behaviour-preserving: the class-forming code
  blocks concatenated in 02-then-03 order compile clean under JDK 21.0.7 `-Xlint:all` and reproduce
  the printed `Demo` output byte-identically (md5 `257ad9e68a1b20b1f1b4680f6d225452`).
- **Row 38 split FOUR ways on 2026-08-28.** §3.6.37-3.6.47 became `05-internals-e-sizing-and-iteration.md` (3.6.37-3.6.40, row 38), `05a-...-e1-removal-and-iteration-order.md` (3.6.41, row 38a), `05a1-...-e1b-iteration-order.md` (3.6.42, row 38b), `05b-...-e2-views-hooks-and-hashtable.md` (3.6.43-3.6.45, row 38c), `05c-...-e4-hashtable-and-prime-modulus.md` (3.6.46-3.6.47, row 38d). Verified from each footer: all 11 leaves owned exactly once. Filenames `05b` and `05c` are deliberately stale after their split (Hashtable moved to 05c) and must NOT be renamed.

- **Row 52 split THREE ways on 2026-08-28.** §3.11's 14 leaves became `04-internals-identity-weak.md` (3.11.1-3.11.3, row 52, 763 — flat interleaved table, identity-hash scramble, probe loops, `closeDeletion` walked term by term at `:619`), `04a-internals-identity-sizing-and-uses.md` (3.11.4-3.11.7, row 52a, 800 — sizing constants, one-null-slot rule, `NULL_KEY`, the contract violation, use cases) and `04b-internals-weak-hash-map.md` (3.11.8-3.11.14, row 52b, 799 — `Entry extends WeakReference`, `expungeStaleEntries`, the clearing sequence's arbitrary gap, `size()` with side effects). A first attempt reached 1300 + 967 and was re-split; nothing was compressed — the 25 lines needed came from two blocks added during the split, not from inherited content. `04`'s filename is deliberately stale and must NOT be renamed.

- **Rows 50 and 51 split on 2026-08-28.** §3.10's 14 leaves became `02-internals-enum-map-set.md` (3.10.1-3.10.7, row 50, 800) and `02b-internals-enum-set.md` (3.10.8-3.10.14, row 50b, 751), seam at `EnumMap` memory arithmetic / `EnumSet.noneOf`. §2.9.7-2.9.16 became `03-identity-and-weak.md` (2.9.7-2.9.9, row 51, 512), `03b-weak-hash-map.md` (2.9.10-2.9.14, row 51b, 672) and `03c-legacy-maps-and-properties.md` (2.9.15-2.9.16, row 51c, 502), seams at the `IdentityHashMap` boxed definition and the end of the reference-strength ladder. `03`'s filename is deliberately stale and must NOT be renamed. Rows 52/52a (§3.11) remain unwritten.

- **Row 40 split SEVEN ways on 2026-08-28.** §3.7's 17 leaves became `01-internals.md` (3.7.1/2/6, row 40), `01a-...-a2-hooks-and-access-order.md` (3.7.4/8, row 40a), `01a1-...-a3-insertion-removal-and-containsvalue.md` (3.7.3/5/7/9, row 40b), `01b-...-b-lru-and-sequenced.md` (3.7.10, row 40c), `01b1-...-b2-access-order-is-a-write.md` (3.7.11/12, row 40d), `01c-...-c-sequenced-and-caching.md` (3.7.13/14, row 40e), `01c1-...-c2-memory-set-and-caffeine.md` (3.7.15/16/17, row 40f). Verified from each file's `Leaves covered` footer: all 17 leaves owned exactly once, no gaps, no overlaps; every file under 600. Filenames are the ones the writers produced and must not be renamed. Nav chain runs 40 -> 40a -> 40b -> 40c -> 40d -> 40e -> 40f -> row 41.

- **§4.1 (row 26) split FIVE ways on 2026-08-26, and this is the pattern for every build-it
  row.** The row's 16 leaves are ~1,800 lines of working implementation against a 480-line
  estimate. A 2-way split overran the ceiling on both halves and dropped 4.1.7–4.1.8; a 4-way
  split still left one file at 737. The 5-way split fits: `05-build-my-array-list.md`
  (4.1.1–4.1.6, row 26, 600), `06-build-my-array-list-b-iterators.md` (4.1.7–4.1.8, row 26b,
  423), `07-build-my-array-list-c-sublist-and-equality.md` (4.1.9–4.1.11, row 26c, 545),
  `08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md` (4.1.12–4.1.13, row 26d, 422),
  `09-build-my-array-list-e-spliterator-diff-and-benchmark.md` (4.1.14–4.1.16, row 26e, 520).
  Every one of the 16 leaves verified present in exactly one file, and **the split is
  behaviour-preserving**: all 14 code blocks concatenated in 05→09 order compile clean under
  JDK 21.0.7 `-Xlint:all` and produce demo output md5 `1d4f72abd453f0d7867db0a38c57cc2a`,
  identical to the original single-file build. Nav chain: `04-amortised-analysis` → `05` → `06`
  → `07` → `08` → `09` → `linked-list/01`.
  **`06-build-my-array-list-b-views-and-bulk.md` (1067 lines) is a superseded dead file.** It is
  referenced by nothing, has no row in the file plan, and its footer falsely claims leaves
  4.1.9–4.1.16 — which now belong to rows 26c/26d/26e. RESOLVED 2026-08-28 without deletion: the user chose to retain it. A SUPERSEDED banner now sits directly under its H1 and its footer no longer claims any leaves, so no reader or aggregate pass can be misled by it. It is excluded from rows 70–73. Agents
  in this pipeline are barred from deleting files.

- **§3.6 (`HashMap` source walk, rows 34–38) split from 5 files into 17 on 2026-08-27.** The
  original plan gave §3.6's 47 leaves five files at 400–460 estimated lines each. Every one of the
  first three overran: row 35 came back at 766, row 36 at 720, row 36's concurrency half at 719.
  The pattern is specific to this section and worth recording, because it is not padding — an
  INTERNALS `HashMap` row carries three costs the estimate did not price: the JDK methods are long
  (`resize()` is 77 lines, `putTreeVal` 36, `split` 51), every `[SOURCE]` line quoted must then be
  explained, and every `[PROVE]` tag needs a compiled-and-run program with its real output on the
  page. Roughly half of a finished file here is inside fences. The splits, all at leaf boundaries:
  - row 34 → `01-internals-a-constants-and-hash.md` (3.6.1–3.6.10, 572) and
    `01b-internals-a2-hash-spread-and-sizing.md` (3.6.11–3.6.16, 580).
  - row 35 → `02-internals-b-put-and-get.md` (3.6.17–3.6.20, 594) and
    `02b-internals-b2-bincount-and-treeifybin.md` (3.6.21, 3.6.22, 385).
  - row 36 → `03-internals-c-resize.md` (3.6.23, 339), `03a-internals-c1-lo-hi-split.md`
    (3.6.24–3.6.26, 566), `03b-internals-c2-concurrent-resize-and-tree-split.md` (3.6.27, 3.6.28,
    483) and `03c-internals-c3-tree-split.md` (3.6.29, 413). **`03b`'s filename retains
    "and-tree-split" from the pre-split plan and is deliberately not renamed** — §3.6.29 lives in
    `03c`. Renaming would have orphaned a written file, and this set already carries one dead file
    that needs a human `rm`; a cosmetically stale filename is the cheaper defect. The file's title,
    footer and leaf list all correctly claim 3.6.27–3.6.28 only.
  - row 37 → `04-internals-d-treeify.md` (3.6.30, 537),
    `04a-internals-d1-puttreeval-and-comparable.md` (3.6.31, 3.6.32, 600),
    `04b-internals-d2-poisson-and-hysteresis.md` (3.6.33, 3.6.34, 486) and
    `04c-internals-d3-collision-dos.md` (3.6.35, 3.6.36, 509).
  Every one of §3.6's 47 leaves is owned by exactly one of these files, and the nav chain runs
  unbroken `priority-queue/05` → `01` → `01b` → `02` → `02b` → `03` → `03a` → `03b` → `03c` → `04`
  → `04a` → `04b` → `04c` → `05`.

- **Row 43 (§3.8.1–3.8.9, `TreeMap` red-black internals) pre-split FIVE ways on 2026-08-27, before dispatch.** A 500-line estimate for 9 `[SOURCE]`/`[PROVE]` leaves plus five manifest diagrams follows the same cost shape the `HashMap` internals rows discovered the hard way (see above): every quoted source line needs explaining and `fixAfterInsertion`/`fixAfterDeletion` are long methods with four and six cases respectively. Split at concept boundaries, one diagram per file: `02-internals-a1-invariants-and-height.md` (3.8.1–3.8.3, D-104), `02b-internals-a2-entry-and-rotations.md` (3.8.4, 3.8.5, D-105), `02c-internals-a3-fixafterinsertion.md` (3.8.6, D-106), `02d-internals-a4-fixafterdeletion.md` (3.8.7, D-107), `02e-internals-a5-deleteentry-and-successor.md` (3.8.8, 3.8.9, D-108). Nav chain: `linked-hash-map/02` → `02` → `02b` → `02c` → `02d` → `02e` → `03`.
- **Row 44 (§3.8.10–3.8.23, `TreeMap` keys/views/alternatives) pre-split THREE ways on 2026-08-27, before dispatch.** 14 leaves and 3 diagrams against a 470-line estimate is past the point where a single INTERNALS file has landed under 600 anywhere in this set. Split: `03-internals-b1-key-identity-and-nulls.md` (3.8.10–3.8.14, no diagram — the identity/nulls leaves are prose-and-proof, not diagram-bearing), `03b-internals-b2-buildfromsorted-and-views.md` (3.8.15–3.8.17, D-109, D-37, D-110), `03c-internals-b3-comparisons-and-alternatives.md` (3.8.18–3.8.23, D-111). D-37 (`TreeMap` range views are range-restricted) lands here rather than in immutable-collections/01 despite its manifest leaf tag 2.3.10, because its subject is `TreeMap`'s `inRange` check, which is exactly what 3.8.16 covers — the file plan's `Diagrams` column for row 44/44b is authoritative. Nav chain: `02e` → `03` → `03b` → `03c` → `04`.
- **Row 44b split again on 2026-08-28: `03b-internals-b2-buildfromsorted-and-views.md` came back at 628 lines**, past the 600-line hard split, even after the row-44 three-way pre-split above. Split at the concept boundary between 3.8.15 and 3.8.16: `03b-internals-b2-buildfromsorted.md` (row 44b1, 3.8.15 alone, D-109a/b/c) and `03b2-internals-b2b-views-and-memory.md` (row 44b2, 3.8.16–3.8.17, D-37, D-110). Nav chain: `03` → `03b` → `03b2` → `03c`.
  **`03b-internals-b2-buildfromsorted-and-views.md` (628 lines) is now a superseded dead file**,
  same category as `array-list/06-build-my-array-list-b-views-and-bulk.md` above: it is
  referenced by nothing (the row 44b1/44b2 nav chain uses `03b-internals-b2-buildfromsorted.md`
  and `03b2-internals-b2b-views-and-memory.md`, distinct filenames), has no row in the file plan,
  and its content is now duplicated and superseded by 44b1+44b2. RESOLVED 2026-08-28 without deletion, per the user ruling that superseded files are retained: it is 636 lines and now carries a `> **SUPERSEDED — DO NOT READ, DO NOT CITE.**` banner directly under its H1 naming rows 44b1/44b2, and its footer no longer claims any leaves. It is deliberately NOT given a plan row (it is not part of the plan) and MUST be excluded BY NAME from the aggregate files, rows 70–73 — a glob-driven pass will otherwise pick it up. No human action outstanding;
  agents in this pipeline are barred from deleting files.
- **Row 45 (§4.6.1, `MyTreeMap`) pre-split FOUR ways on 2026-08-27, before dispatch, per the §4.1/§4.5 build-it precedent.** One syllabus leaf, but the deliverable is a complete generic red-black tree map with insert, delete, navigation and an iterator — the array-list build-it row split 16 leaves into 5 files at a similar per-file code density, and `fixAfterDeletion` alone is longer than `fixAfterInsertion`. Split: `04-build-my-tree-map.md` (fields, `compare`, `getEntry`, rotations, `put`+`fixAfterInsertion`), `04b-build-my-tree-map-b-deletion.md` (`deleteEntry` successor swap + `fixAfterDeletion`'s six cases), `04c-build-my-tree-map-c-navigable-and-iterator.md` (the six `NavigableMap` entry accessors + in-order iterator), `04d-build-my-tree-map-d-diff-and-demo.md` (diff table + compile-and-run demo + md5). All four carry leaf 4.6.1; the leaf ledger records this as "one leaf, four files" rather than fabricating sub-leaf numbers the syllabus does not have. Nav chain: `03c` → `04` → `04b` → `04c` → `04d` → `sets/01`.
  **Row 45b split again on 2026-08-28: `04b-build-my-tree-map-b-deletion.md` came back at 721
  lines**, past the 600-line ceiling — `fixAfterDeletion` was, as flagged in advance, the densest
  method in the whole series. Split at the case boundary: `04b-build-my-tree-map-b-deletion.md`
  (row 45b1, `remove`/`successor`/`deleteEntry`'s successor swap + `fixAfterDeletion` cases A and
  B) keeps its original filename, and `04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md`
  (row 45b2, cases C and D + the left/right mirror + the deletion demo + this part's Pitfalls/
  Cheat sheet/Self-test/footer) is new. The five build-it files are now numbered part 1–5 of 5,
  not 1–4 of 4: `04` (part 1), `04b` (part 2), `04b2` (part 3), `04c` (part 4), `04d` (part 5).
  Nav chain: `03c` → `04` → `04b` → `04b2` → `04c` → `04d` → `sets/01`.
  **Corrected 2026-08-28:** `04-build-my-tree-map.md`'s header/prose/footer, and `04b`'s and
  `04b2`'s "part N of 5" text, were swept and fixed to the current "part N of 6" numbering after
  the second split below made even that stale.
  **Row 45c split again on 2026-08-28: `04c-build-my-tree-map-c-navigable-and-iterator.md`
  came back at 654 lines**, past the 600-line ceiling. Split at the concept boundary between the
  six navigable entry accessors and the iterator: `04c-build-my-tree-map-c-navigable-and-iterator.md`
  (row 45c1, keeps its filename, now covers only `firstEntry`/`lastEntry`/`floorEntry`/
  `ceilingEntry`/`lowerEntry`/`higherEntry`) and `04c2-build-my-tree-map-c2-iterator.md` (row
  45c2, the fail-fast in-order `Iterator` + the `ConcurrentModificationException` demo). The
  build-it series is now 6 files, part 1–6 of 6: `04` → `04b` → `04b2` → `04c` → `04c2` → `04d`.
  **Behaviour-preserving proof run 2026-08-28 — canonical record, consolidated after three
  harness passes.** All six shipped files' code has been extracted, compiled, and run multiple
  times; four different md5s appear in this row's history because three passes used three
  different harness *assemblies*, not because any pass fabricated a result — **the md5 is a
  property of the notes plus the harness, not of the notes alone.** History, oldest to newest:
  (1) a first pass patched the *harness* (not the shipped files) to get a compile, and reported a
  third, nonexistent bug (`04c2` calling a no-arg `getFirstEntry()` — retracted; the shipped file
  always called the correct one-arg `getFirstEntry(root)`). Its md5,
  `81c80d60c7e78f0b4a32d2af09fe90e2`, is retracted along with the harness-patch methodology. That
  pass did find two real bugs, since fixed directly in the shipped files, not just the harness:
  `Entry<K,V>` in `04-build-my-tree-map.md` now `implements Map.Entry<K,V>` with
  `getKey()`/`getValue()`/`toString()` added next to the existing `setValue()`, matching real
  `java.util.TreeMap.Entry` exactly (see `02b-internals-a2-entry-and-rotations.md`'s source
  excerpt). (2) A clean re-extraction ran only `04d`'s six demo blocks, skipping `04c`'s and
  `04c2`'s own demo snippets entirely → `713593a58eba9b6397f50ec9ec527f82`. (3) A fuller
  extraction additionally running `04c`'s floor/ceiling/lower/higher demo and all three of
  `04c2`'s iterator/CME/`IllegalStateException` demos, with the second, otherwise-uncaught
  `it3.remove()` call in `04c2`'s third demo block left exactly as the shipped source shows it —
  no `try`/`catch` added — so the process terminates there and nothing from `04d`'s section ever
  prints → `d393e9a1875c77d89daaffe16b2bd5e8`. (4) The same fuller extraction, but with that one
  uncaught `IllegalStateException` wrapped in `try { … } catch (IllegalStateException ise) {
  System.out.println("caught: " + ise); }` — a harness-assembly choice so the process survives to
  reach `04d`'s demos too, not a fix to any shipped file — →
  `2e25f2a9af71f7e984001d8b8e306b26`. **This last number is canonical for this row.** It has been
  independently reproduced twice on 2026-08-28 from the shipped files as they currently stand
  (post the `Entry`/`Map.Entry` fix; `04`, `04c`, `04c2` have had only prose/header edits since,
  verified line-for-line against the code blocks below — zero code-block diffs), with compiled
  class files left on disk at `/tmp/jc-row45/out/` and `/tmp/jc-row45b/out/` as evidence. An
  earlier note at this point calling `2e25f2a9…` "unverified"/"could not be reproduced" was
  itself wrong and is superseded.
  **Pinned harness, superseded 2026-08-28 (see below): reproduced `2e25f2a9af71f7e984001d8b8e306b26`
  via a harness-level `try`/`catch` around `it3.remove()` — that wrapping is no longer needed.**
  class members concatenated
  in file order — `04`'s 5 blocks; `04b`'s `remove`/`successor`/`deleteEntry` + `fixAfterDeletion`'s
  opening with cases A/B (3 blocks); `04b2`'s 2 blocks spliced into that same `fixAfterDeletion`
  body as the case-B/C/D continuation and the right-child mirror `else` (one method, not two);
  `04c`'s `getFirstEntry`/`getLastEntry`/`firstEntry`/`lastEntry` and the four `get*Entry`
  navigable-accessor blocks (2 of its 4 blocks); `04c2`'s `EntryIterator`/`entryIterator()` (1 of
  its 4 blocks). Excluded: `04c`'s `floorEntryWrong` counter-example (marked "WRONG … is not what
  the JDK does"); `04`'s and `04c`'s own section-level worked-example `main` methods are kept as
  ordinary (if unused) class/inner-class members — `04`'s stays inside `MyTreeMap` and is never
  the entry point actually run. Demo statements — `04c` block 2 (floor/ceiling/lower/higher),
  `04c2` blocks 1–3 (sorted print, CME trace, `IllegalStateException` trace), `04d`'s 6 blocks —
  assembled into one `Demo.main`, each file's snippets wrapped in its own `{ }` scope (avoids
  reusing the local name `m` across `04c`'s and `04c2`'s independent demos). At the time,
  the one behavioral addition anywhere was the `try`/`catch` around `04c2`'s second
  `it3.remove()` described above; every other statement was verbatim. Commands:
  `javac -Xlint:all -d <out> MyTreeMap.java` then `java -cp <out> 'MyTreeMap$Demo' | md5` (JDK
  21, `/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/bin/`). Result: zero `javac`
  errors, zero `-Xlint:all` warnings, and every `//` comment across `04c`, `04c2`, and `04d`
  matched the real printed output exactly.
  **Fixed 2026-08-28, item 29:** `04c2-build-my-tree-map-c2-iterator.md`'s
  `it3.remove()` demo now carries the `try`/`catch` (printing the caught
  `IllegalStateException`) directly in the shipped note, not just the harness — see item 29's
  resolution below. Re-proved from the shipped files as they now stand, in `/tmp/jc-row45c/`,
  with **no harness-level behavioral wrapping at all**: same block selection and `{ }`-per-file
  scoping as above, `javac -Xlint:all -d /tmp/jc-row45c/out MyTreeMap.java` then
  `java -cp /tmp/jc-row45c/out Demo` piped to `md5`. Zero `javac` errors, zero `-Xlint:all`
  warnings, and the stdout byte-for-byte matches the prior harness-wrapped run:
  **`2e25f2a9af71f7e984001d8b8e306b26`, unchanged** — the fix moved the `try`/`catch` from the
  harness into the note without changing a single byte of output. Every `//` comment across
  `04c`, `04c2`, and `04d` still matches the real printed output exactly, including the new
  `caught: java.lang.IllegalStateException` line `04c2` now prints itself. No open item remains
  for this row.
  **One accepted overage:** the `Entry implements Map.Entry` fix added ~16 lines of real code
  (`getKey`/`getValue`/`toString`) to `04-build-my-tree-map.md`, pushing it from 600 to 614 —
  over the 600-line hard ceiling by 14 lines after two rounds of trimming only the prose *added*
  by this fix (not the file's original teaching content, which was left untouched per house
  rules). A seventh split of an already six-part series for 14 lines was judged worse than a
  documented small overage; flagged here rather than left silent.

- **§4.3 (row 39) split EIGHT ways on 2026-08-27**, the widest build-it split in the set, and it
  followed the §4.1 precedent of proving the split rather than asserting it. §4.3's 14 leaves are
  three public classes (`MyHashMap`, `MyHashSet`, `MyLinkedHashMap`) plus `LruCache`, a demo harness
  and a benchmark, against a 560-line estimate. The eight files, in nav order:
  `06-build-my-hash-map.md` (4.3.1, 4.3.2, 431), `06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md`
  (4.3.3, 356, carries D-146a–d), `07-build-my-hash-map-b-put-get-resize.md` (4.3.4–4.3.6, 530),
  `08-build-my-hash-map-c-treeify-and-defaults.md` (4.3.7, 4.3.8, 584),
  `09-build-my-hash-map-d-views-and-iterator.md` (4.3.9, 4.3.10, 418),
  `10-build-my-hash-map-e-set-linked-and-diff.md` (4.3.11, 4.3.12, 599),
  `10a-build-my-hash-map-f-the-demo-harness.md` (no new leaves — `Demo.java` and the differential
  test, 509) and `10b-build-my-hash-map-g-diff-and-collision-dos.md` (4.3.13, 4.3.14, 377, carries
  D-147). **The split is verified behaviour-preserving**: every `java` block extracted from the eight
  files in nav order and concatenated per its `// <File>.java` label compiles under JDK 21.0.7+8-LTS-245
  with `-Xlint:all` at zero warnings and zero errors, and the demo produces output md5
  `4dd3a26f8346237a6d5929a8952b8a25`.
  **HARNESS PIN (item 28).** Inclusion rule, purely mechanical: a fence must be tagged `java`
  AND its first line must full-match `// (\w+\.java)`. **24 blocks included**, per label
  `MyHashMap.java` 17 (4 from page 06, 2 from 06a, 4 from 07, 4 from 08, 3 from 09 — the class's
  closing brace is in 09's last block), `MyHashSet.java` 1, `MyLinkedHashMap.java` 1,
  `LruCache.java` 1 (all page 10), `Demo.java` 3 (page 10a), `Bench.java` 1 (page 10b).
  **Excluded: 41** `java` blocks lacking the label, **plus 36** untagged fences — the JDK source
  quotes sit in bare fences with no language tag so they can never reach the extractor. One
  near-miss label in page 08 is deliberately worded to fail the regex so the recursive-CME
  snippet shows for contrast without double-including. **No splicing** — pure ordered append,
  and **block order is load-bearing**: `MyHashMap.java` blocks 2-17 are class-body continuations
  and `Demo.java` block 2 is a bare continuation of `main`. Digest covers **stdout only**, one
  `java Demo` run, 118 deterministic lines, seed 42, no timings; `Bench` output is excluded
  because it prints wall-clock. BSD `md5`, not `md5sum`. **Independently reproduced 2026-08-28**
  by re-deriving the classification from the published pages alone: 24 included with identical
  per-label counts, 41 + 36 excluded — see Open questions item 38.
  Six code labels rather than the planned four: `MyHashMap.java`,
  `MyHashSet.java`, `MyLinkedHashMap.java`, `LruCache.java`, `Demo.java`, `Bench.java` — `LruCache`
  had to be its own top-level file because as a nested class its block would have preceded `Demo`'s
  class header in concatenation order. Nav chain: `05c` → `06` → `06a` → `07` → `08` → `09` → `10` →
  `10a` → `10b` → `../linked-hash-map/01-internals.md`.
  **Harness pinned (item 28), and the md5 independently reproduced by the orchestrator on 2026-08-28**
  from a clean extract-compile-run rather than taken on the writer's report:
  - *Two independent exclusion rules.* **Rule A, at fence level:** every JDK source quote sits in a
    bare ``` fence with **no language tag**, so it never reaches the extractor at all. **Rule B, at
    label level:** a fenced `java` block counts as source if and only if **its first line full-matches
    `// <Name>.java`**. The extractor prints every `java` block it skips, so the Rule-B exclusion set
    is enumerated rather than assumed. One block in `08` is worded to *deliberately* fail the regex
    (`// (excerpt from Demo.java section 8 -- the full file is assembled in 10a)`) so the recursive-CME
    snippet can be shown for contrast without being double-included.
  - *Included:* **24 labelled blocks, 1,363 lines**, concatenated in page order per label —
    `MyHashMap.java` 706 lines from **17** blocks, `MyLinkedHashMap.java` 235 from 1,
    `Demo.java` 278 from 3, `Bench.java` 96 from 1, `MyHashSet.java` 32 from 1, `LruCache.java` 16 from 1.
  - *Excluded:* **41 `java` blocks** — wrong-then-right pitfall pairs, non-compiling counter-examples
    and contrast fragments. Per file: 06=6, 06a=8, 07=6, 08=5, 09=6, 10=6, 10a=0, 10b=4.
    **Re-counted by the orchestrator after the final prose edits**, so this is verified-after, not
    verified-before.
  - *Splicing:* **none** — but **block order is load-bearing, not merely tidy.** `MyHashMap.java`
    blocks 2–17 are bare *class-body member sequences* with no class header, and block 17 supplies the
    closing `}`. `Demo.java` block 1 opens `class Demo` and `main`, **block 2 is a bare statement
    sequence continuing `main`'s body**, and block 3 closes `main` then adds the helper methods and the
    class brace. Reorder any of them and it does not compile — the desired failure mode.
  - *Wrapping:* none applied in the harness. The one deliberately-throwing example (in `08`) is inside
    `try`/`catch` **in the published code**, so it is item-29 compliant and the md5 is over
    unmodified page content.
  - *Commands:* `javac -Xlint:all -d <out> <the six extracted .java files>` → zero output, zero
    warnings; then `java -cp <out> Demo > demo.out`; then `md5 demo.out`. JDK
    `/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home`, build 21.0.7+8-LTS-245, Apple M4 Pro
    arm64.
  - *Coverage:* the md5 is over **`Demo`'s stdout only**, from a single `java Demo` invocation — no
    `2>&1`, and not `Bench`, whose wall-clock timings are deliberately unpublished and could never be
    reproducible. 118 lines, 16 sections, fully deterministic: the differential test uses a fixed seed
    of 42 and `Demo` contains no timings. Both deliberately-provoked
    `ConcurrentModificationException`s (recursive `computeIfAbsent`; structural `put` during iteration)
    are caught **in the published code** and print a caught-as-expected line that is part of the
    digest, so the JVM exits 0 and no stream is ever truncated. That has a useful corollary: a
    transcription that *drops* a `try`/`catch` changes the digest rather than silently truncating it —
    the failure becomes visible, which is what item 28 wants. Three separate runs agree: the writer's
    original build, its extraction rebuild, and the orchestrator's independent rebuild.

- **§3.7 (row 40) ended up split SEVEN ways, in three successive passes, 2026-08-27/28.** The first
  cut (below) was not enough: both halves overran again, and so did one of their halves. Final
  layout, every cut at a leaf boundary: `01-internals.md` (3.7.1, 3.7.2, 3.7.6, 472, D-100),
  `01a-internals-a2-hooks-and-access-order.md` (3.7.4, 3.7.8, 533, D-101),
  `01a1-internals-a3-insertion-removal-and-containsvalue.md` (3.7.3, 3.7.5, 3.7.7, 3.7.9, 442),
  `01b-internals-b-lru-and-sequenced.md` (3.7.10, 519, D-102a–d),
  `01b1-internals-b2-access-order-is-a-write.md` (3.7.11, 3.7.12, 353),
  `01c-internals-c-sequenced-and-caching.md` (3.7.13, 3.7.14, 565, D-103),
  `01c1-internals-c2-memory-set-and-caffeine.md` (3.7.15, 3.7.16, 3.7.17, 361). All seven under the
  600 ceiling. **Two filenames are deliberately stale and must not be renamed:** `01b`'s
  "and-sequenced" (the `SequencedMap` material is in `01c`) and `01c`'s "and-caching" (the Caffeine
  material is in `01c1`). Renaming would orphan written files; a stale filename is the cheaper
  defect, and every title, footer and leaf list correctly claims only its real leaves.

- **§4.6.2 and §4.6.3 (row 41) split into four files on 2026-08-28 — and each leaf is deliberately
  split across two files.** This is the one case the folder law permits it: a single primary concept
  whose working code exceeds the ceiling. §4.6.2's `LruCache` plus its property test is
  `02-build-lru-by-hand.md` (599) and `02a-build-lru-b-proof-and-cost.md` (520); §4.6.3's `LfuCache`
  plus the policy comparison is `03-build-lfu-sketch.md` (583) and
  `03a-build-lfu-b-policy-comparison.md` (325). The row's working code alone is 765 lines of Java
  across 8 source files, against a 400-line estimate. **The split is verified behaviour-preserving:**
  all 8 files extracted from the four pages, concatenated per their `// <File>.java` labels, compile
  under JDK 21.0.7+8-LTS-245 with `-Xlint:all` at zero warnings and zero errors, the extracted
  sources are byte-identical to the tested originals, and the concatenated demo output has md5
  `30b06125da80902601e1911f9792a500`.
  **HARNESS PIN (item 28).** Inclusion rule: first line matches `^//\s*([A-Za-z0-9_]+\.java)$`.
  **8 labelled blocks, one block per label, no label split across blocks**, in nav order:
  `LruCache` and `LruDemo` (page 02), `BrokenLruCache` and `LruProofDemo` (02a), `LfuCache`,
  `BuggyLfuCache` and `LfuDemo` (03), `PolicyDemo` (03a). 30 `java` blocks exist across the four
  pages; **22 excluded** — 3 JDK source quotes, 3 bare-statement contrast fragments, 16 Pitfall
  wrong/right blocks. **No splicing anywhere**; every built file is a whole compilation unit.
  `BuggyLfuCache.java` **is in the build** — it compiles, runs and contributes to the digest; it
  is wrong as a cache, not absent from the harness. The digest covers **stdout and stderr merged
  (`2>&1`)**, not stdout alone; stderr contributed nothing because the one throwing snippet is
  caught and printed to stdout from the published `LfuDemo` block, which is byte-identical to
  what was compiled — so no stream was truncated and item 29 is satisfied in the notes, not the
  harness. Working directory `/tmp/jc-write-row41-private/verify2/`, seed `Random(20260828L)`.
  Nav chain: `01c1` → `02` → `02a` → `03` → `03a` →
  `../tree-map/01-navigable-api.md`.
  **Harness pinned (item 28), and the md5 independently reproduced by the orchestrator on 2026-08-28.**
  Same inclusion rule as §4.3's Rule B — a `java` block is source only if its first line matches
  `^//\s*([A-Za-z0-9_]+\.java)$`, a lone comment naming a file and nothing else on the line. No
  inference from content, and nothing excluded is ever repaired, wrapped or spliced to make it compile.
  - *Included:* **8 labelled blocks, one per label**, so no label needed concatenating from parts —
    `LruCache.java` and `LruDemo.java` (page 02), `BrokenLruCache.java` and `LruProofDemo.java` (02a),
    `LfuCache.java`, `BuggyLfuCache.java` and `LfuDemo.java` (03), `PolicyDemo.java` (03a).
    `BrokenLruCache` and `BuggyLfuCache` are **deliberate counter-examples that are part of the
    build**, because each page instantiates them alongside the correct class and prints the divergence;
    they contribute to the digest and are not excluded.
  - *Excluded:* **22 of the 30 `java` blocks** across the four pages (11/6/9/4 per page) — JDK source
    quotes, bare-statement contrast fragments (the sentinel versus null-terminated `unlink`; a
    four-statement excerpt of `LruCache.evict()`), and wrong-then-right pitfall pairs. Per page: 02=9,
    02a=4, 03=6, 03a=3.
  - *Splicing:* **none.** All 8 labelled blocks are whole compilation units, first line to closing
    brace. The three fragments that *would* have needed splicing are unlabelled, so the extractor never
    touched them and no method was reassembled from parts.
  - *Wrapping:* none applied in the harness. `BuggyLfuCache`'s `NullPointerException` is caught in the
    **published** code (`03-build-lfu-sketch.md` lines 351–354, caught output at 383) and printed as
    the lesson, so a reader typing the page out sees the diagnosis rather than a crash. This is exactly
    the case item 28 was written for, and the answer is that the wrap is on the page, not in the harness.
  - *Commands:* `javac -Xlint:all` over the 8 extracted files → zero warnings; then four separate
    runs, `java -cp <dir> LruDemo`, `LruProofDemo`, `LfuDemo`, `PolicyDemo`, each redirected to its own
    file; then `cat` of the four **in that order** piped to `md5`. JDK
    `/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home`, build 21.0.7+8-LTS-245, Apple M4 Pro
    arm64.
  - *Coverage:* **stdout and stderr merged** — every run used `2>&1`, appending to one 62-line file.
    The orchestrator first recorded this as stdout-only, which was wrong; the writer corrected it. The
    two are byte-identical here because the only throwing snippet is caught and printed to stdout, and
    an independent **stdout-only** reproduction returned the same digest — which is now the evidence
    that stderr contributed nothing, rather than an assumption that it could not have. Record it as
    merged, because that is what was run.
  - *Determinism pin:* `LruProofDemo` seeds `new Random(20260828L)`, which fixes the
    165,240/119,792/14,968 operation split and the final `[5, 2, 6, 0, 7]` recency order.
    `LfuDemo` and `PolicyDemo` use no randomness. Section numbering runs continuously across both
    split pairs (`1.`/`2.` on 02 and 03, `3.`/`4.` on 02a and 03a), which is why each split file's
    transcript starts mid-sequence — stated in the opening paragraph of 02a and 03a.
  - Three runs agree: the writer's original build, its extraction rebuild (`diff -q` clean against the
    originals, all 8 files byte-identical), and the orchestrator's independent run of the rebuilt
    classes.

- **§3.7 (row 40) first cut on 2026-08-27.** `linked-hash-map/01-internals.md` came back at 935 lines
  against a 470 estimate. Leaves 3.7.1, 3.7.2 and 3.7.6 (the overlay and the four allocation
  overrides, with D-100) stay in `01-internals.md`; 3.7.3, 3.7.4, 3.7.5, 3.7.7, 3.7.8 and 3.7.9 (the
  three hooks, access order, `containsValue` and `removeEldestEntry`, with D-101) move to
  `01a-internals-a2-hooks-and-access-order.md`. The seam is a concept boundary: allocation closes the
  first file, notification opens the second. Nav chain: `hash-map/10b` → `01-internals` → `01a` →
  `01b` → `02-build-lru-by-hand` → `03-build-lfu-sketch` → `../tree-map/01-navigable-api.md`.

- **Row 46 (§3.9, Sets over Map) split on 2026-08-28.** `sets/01-set-over-map.md` came back at
  739 lines against a 380 estimate. Split at the concept boundary between the core mechanism and
  the sibling family: `sets/01-set-over-map.md` (row 46a, keeps its filename, 3.9.1–3.9.5: the
  `PRESENT` dummy, `add`-as-`put`, the `LinkedHashSet` dummy-boolean constructor, every `HashMap`
  fact transferring, the memory arithmetic, D-112) and `sets/01b-set-over-map-siblings-and-exceptions.md`
  (row 46b, 3.9.6–3.9.9: the wider set-over-map family plus who breaks the pattern
  (`CopyOnWriteArraySet`, `EnumSet`), D-113). Nav chain: `tree-map/04d` → `01` → `01b` →
  `02-set-algebra`.
- **Row 47 (§2.12, set algebra) split on 2026-08-28.** `sets/02-set-algebra.md` came back at 692
  lines against a 400 estimate. Split at the concept boundary between the core four operations and
  the trap/beyond material: `sets/02-set-algebra.md` (row 47a, keeps its filename, 2.12.1–2.12.3:
  the four operations as ∪/∖/∩, the O(n·m) `removeAll` cost trap, `AbstractSet.removeAll`'s size
  branch, D-59/D-60) and `sets/02b-set-algebra-traps-and-beyond.md` (row 47b, 2.12.4–2.12.10: the
  `keySet().retainAll` mutation, the immutable-`removeAll` short-circuit question, the mutable-
  element stranding bug, `disjoint`, symmetric difference, missing multiset semantics, `EnumSet`
  bulk ops). Nav chain: `01b` → `02` → `02b` → `03-bitset`.

- **Rows 62–69 (§2.6/§2.7, §2.8, §2.11, §2.13, §2.16, §2.17, §4.6-remainder) written 2026-08-28.**
  No file splits — all eight rows landed as planned, one row each. Diagram frame splits recorded:
  D-43 (rotate by three reversals) → D-43a/b/c/d, one file per frame; D-45 (TimSort run detection)
  → D-45a/b/c; D-48 (dual-pivot partition) → D-48a/b/c; D-62 (groupingBy with downstreams) →
  D-62a/b/c/d. These are frame splits per the diagram spec's "prefer several small diagrams" rule,
  not manifest substitutions — every D-NN id from the manifest lands, just as more than one file.
  No manifest departures on any of D-42–D-50, D-58, D-62, D-122, D-149, D-150 — the illustrator
  pass verified every mechanism (`Collections.rotate2`'s reversal boundaries, `TimSort.minRunLength`'s
  shift-and-OR computation, `DualPivotQuicksort`'s less/great/k partition scheme, `mergeCollapse`'s
  invariants and the de Gouw stack-enlargement fix, `Map` default-method null semantics,
  `ImmutableCollections.CollSer`) against JDK 21 source before drawing, and reported zero
  corrections needed. D-122 is jointly embedded by this row's `utilities/06-serialization.md`
  (row 67) and `immutable-collections/04-internals-immutable-collections.md` (row 56, a different
  session's lane) — the file did not exist when the illustrator checked, so it was authored fresh
  here; row 56's writer should find it present and embed the same path, not recreate it.
  **One real defect found and fixed post-write:** row 67's `utilities/06-serialization.md` shipped
  a JDK-source quote for `HashMap.readObject` containing a placeholder elision
  (`// ... threshold recomputed from cap and lf ...`) inside the fenced code block, violating the
  no-elisions-in-quoted-source rule. Replaced with the real lines
  (`double dc = Math.min(Math.ceil(mappings/(double)lf), (double) MAXIMUM_CAPACITY); int cap = ...;
  float ft = (float) cap * lf; threshold = ...;`), verified against the OpenJDK `HashMap.java`
  source via web search. No other elisions found across rows 62–69 on a full sweep.
  **Row 69 (`build-it/01-supporting-builds.md`) behaviour-preserving proof, pinned per item 28's
  policy.** Seven hand-built structures (`RingBuffer`, `MyMultimap`, `MyBiMap`, `IntArrayList`,
  `MyLinkedList`+`Spliterator`, `CheckedListGuard`, `CmeHarness`) plus one `Demo` class, extracted
  to `/tmp/jc-row69-buildit/src/*.java` (an uncontended scratch path — distinct from the contended
  `/tmp/jc-build-linkedlist/`). One counter-example (the naive cleanup-free `Multimap` sketch, 4.6.5)
  is prose-only and excluded from the compile by design. All demo statements spliced into one
  `Demo.main`, no name collisions. Requirement 1 (verbatim-runnable) applied throughout: every
  deliberately-thrown exception (`RingBuffer.poll()` on empty, `CheckedListGuard`'s
  `ClassCastException`, all four `CmeHarness` CME variants) is wrapped in try/catch printing the
  caught exception, so a reader typing the file in order reaches the end with no uncaught crash —
  the exact defect flagged as open item 29 elsewhere in this index, applied here from first write
  rather than retrofitted. Two real bugs were caught by actually compiling and running (not by the
  harness alone): a `NodeSpliterator.tryAdvance` split-boundary over-consumption bug, and a
  `CmeHarness.removeDuringForEach()` demo that removed the wrong element and silently produced no
  exception — both fixed in the shipped source, not patched only in the harness. Commands, run from
  `/tmp/jc-row69-buildit/`: `javac -Xlint:all -d out src/*.java` (zero errors, zero warnings), then
  `java -cp out Demo > stdout.txt 2>&1`, then `md5 stdout.txt`. Result, reproduced identically
  across three separate runs: **`fea200ff681cbb6bb80e679f4e3b2192`**. Landed at 763 lines — over
  the 600-line target but under the 800-line hard cap per item 27's policy; the excess is seven
  complete compiling classes plus the pinned build-proof section and the required ending, not
  padding (a raw draft ran to 1101 lines and was cut by consolidating the eight-beat prose per leaf
  into tighter combined paragraphs and reflowing line-wrap, not by removing code, tables, diagrams,
  or build-proof content).
  Nav chain: `utilities/07-third-party.md` → `build-it/01-supporting-builds.md` → `90-interview-basics.md`.

- **Rows 49–56 (`specialised-maps/`, `immutable-collections/`) split repeatedly on 2026-08-28, and the
  pattern is now predictable enough to plan for.** Every row in this lane carrying **10 or more
  syllabus leaves came back between 1004 and 1300 lines** against 440–460-line estimates — rows 50
  (1251), 51 (1004), 52 (1300), 53b (1291) and 54 (1030). None of it was padding: the same three
  costs item 27 identified apply here too, plus a fourth specific to these sections — these classes
  are *small*, so a `[SOURCE]` obligation means quoting a method in full rather than excerpting it,
  and `[PROVE]` on a GC- or JVM-timing claim needs a bounded honest harness plus its transcript plus
  a paragraph explaining what the transcript does and does not establish. **Lesson applied mid-lane:**
  from row 52 onward, rows were **pre-split at planning time** at class or concept boundaries before
  dispatch, and those pre-split rows landed inside the cap first time. The splits, all at leaf
  boundaries, none scattering a method or class across files:
  - row 50 → `02-internals-enum-map-set.md` (3.10.1–3.10.7, 800) and `02b-internals-enum-set.md`
    (3.10.8–3.10.14, 751). Seam: `EnumMap` memory closes part 1, `EnumSet.noneOf`'s Regular/Jumbo
    choice opens part 2.
  - row 51 → `03-identity-and-weak.md` (2.9.7–2.9.9, 512), `03b-weak-hash-map.md` (2.9.10–2.9.14,
    672) and `03c-legacy-maps-and-properties.md` (2.9.15–2.9.16, 502).
  - row 52 → `04-internals-identity-weak.md` (3.11.1–3.11.3, 763) and
    `04a-internals-identity-sizing-and-uses.md` (3.11.4–3.11.7, 800). Seam: `closeDeletion` closes
    part 1, the sizing constants open part 2.
  - row 53b → `01b-map-views-and-arrays-aslist.md` (2.3.6–2.3.9),
    `01c-treemap-range-and-reversed-views.md` (2.3.10–2.3.11) and `01d-arrays-aslist.md`
    (2.3.12–2.3.13). Taken as a three-way rather than the writer's proposed two-way, because the
    two-way left one half at 630 — over the 600 cap that applies to INTERMEDIATE files.
  - row 54 → `02-immutable-factories.md` (2.3.14–2.3.16) and
    `02a-shallow-immutability-and-boundaries.md` (2.3.17–2.3.19).
  - rows 53, 54b, 55, 55b, 56, 56b, 56c were pre-split before dispatch on the same reasoning.
  **Four filenames in this lane are now deliberately stale and must NOT be renamed**, per the
  precedent already set by `hash-map/03b`, `hash-map/05b` and `hash-map/05c`:
  `specialised-maps/02-internals-enum-map-set.md` covers only `EnumMap`;
  `specialised-maps/03-identity-and-weak.md` covers only `IdentityHashMap`;
  `specialised-maps/04-internals-identity-weak.md` covers only `IdentityHashMap`'s table and probing;
  `immutable-collections/01b-map-views-and-arrays-aslist.md` covers only the three `Map` views.
  Renaming would orphan a written file; a cosmetically stale filename is the cheaper defect. Every
  one of them carries a line of opening prose saying what it actually covers and where the rest went.
  **No file was deleted or superseded in this lane** — each split kept the original path as part 1
  and added new siblings, so there are no dead files to clean up.

- **`immutable-collections/` (rows 53–56) ended up as 19 files from 4 planned rows, and the
  arithmetic is worth stating because it predicts the cost of any future §-of-this-shape row.**
  Rows 53–55 were dispatched at their planned width and every one overran: 53b came back at 1291,
  54 at 1030, 54b at 669, 55 at 789, 55b at 879. Rows 56/56b/56c were pre-split three ways before
  dispatch on that evidence — and **two of the three still overran**, 56b at 1128 and 56c at 1223,
  because a `[SOURCE]`-tagged leaf in this section means quoting a whole small method rather than
  excerpting a large one, and every `[PROVE]` needed a compiled program plus its transcript plus a
  paragraph bounding what the transcript establishes. Final splits, all at concept boundaries:
  - row 53b → `01b-map-views-and-arrays-aslist.md` (2.3.6–2.3.9, 632),
    `01c-treemap-range-and-reversed-views.md` (2.3.10–2.3.11, 656), `01d-arrays-aslist.md`
    (2.3.12–2.3.13, 504). Taken as a three-way rather than the writer's two-way, whose 630-line half
    would have breached the INTERMEDIATE cap.
  - row 54 → `02-immutable-factories.md` (2.3.14–2.3.16, 673) and
    `02a-shallow-immutability-and-boundaries.md` (2.3.17–2.3.19, 598).
  - row 55 → `03-immutability-tiers.md` (2.4.1–2.4.5, 600) and
    `03a-immutability-tiers-comparison-table.md` (2.4.6 alone, 459). One leaf is a legitimate file
    here because its deliverable is a seven-column verified matrix, the harness that fills it, and a
    two-JVM order proof.
  - row 55b → `03b-immutability-tiers-b-factory-rules.md` (2.4.7–2.4.10, 602) and
    `03c-null-queries-and-guava.md` (2.4.11–2.4.13, 647).
  - row 56b → `04b-internals-open-addressing-and-salt.md` (3.12.6–3.12.8) and
    `04b2-internals-salt-cds-and-null-hostility.md` (3.12.9–3.12.12).
  - row 56c → `04c-internals-mutators-serialization-and-views.md` (3.12.13–3.12.14),
    `04d-internals-sublist-and-reversed-view.md` (3.12.15–3.12.16),
    `04e-internals-layout-and-legacy-factories.md` (3.12.17–3.12.18).
  **Row 54b was accepted at 669 rather than split** — 69 lines over target, and splitting it would
  have added ~120 lines of duplicated ending while moving the §2.3 decision table one file further
  from the material it summarises. Six files here sit at 602–795 and are accepted under item 27's
  policy: `01b` (632), `01c` (656), `02` (673), `02b` (669→693), `03b` (602), `03c` (647), `04` (795).
  **Two more filenames are deliberately stale and must NOT be renamed:**
  `01b-map-views-and-arrays-aslist.md` covers only the three `Map` views (`Arrays.asList` moved to
  `01d`); `04b-internals-open-addressing-and-salt.md` covers only the table (the salt moved to
  `04b2`); `04c-internals-mutators-serialization-and-views.md` covers only mutators and the proxy
  (the views moved to `04d`). No file in this lane was deleted or superseded.

- **DIAGRAM DUPLICATION — 11 manifest ids have two SVGs each, and they need a human `rm`.**
  Two lanes ran illustrator passes over the same flat, topic-scoped `diagrams/` folder before the
  row-ownership collision in item 64 was discovered. Both members of each pair are source-verified
  and correct; this is redundancy, not error. The **canonical** slug per id is the one embedded by
  the note file that owns the row, and the other is an orphan that will trip the self-verify
  script's "orphaned, never embedded" check:
  | id | canonical (embedded) | orphan (delete) |
  |---|---|---|
  | D-121 | `D-121-listof-vs-arraylist-memory.svg` | `D-121-list12-vs-arraylist-bytes.svg` |
  | D-126 | `D-126-chm-bin-level-concurrency.svg` | `D-126-chm-bin-concurrency.svg` |
  | D-127 | `D-127-spread-and-reserved-sign-bit.svg` | `D-127-spread-reserved-sign-bit.svg` |
  | D-128a–d | `D-128a-chm-transfer-strides.svg` and siblings | `D-128a-resize-frame1-setup.svg` and siblings |
  | D-130 | `D-130-chm-striped-counters.svg` | `D-130-size-striped-counters.svg` |
  | D-133 | `D-133-cow-crossover.svg` | `D-133-cow-cost-model.svg` |
  | D-136a–d | `D-136a-ms-queue-lagging-tail.svg` and siblings | `D-136a-msqueue-frame1.svg` and siblings |
  D-121's canonical choice honours item 64's explicit cross-lane request; row 56 embeds it, and the
  extra content the orphan carried (both `ArrayList` byte shapes, `EXPAND_FACTOR = 2`, `List12`'s
  real `EMPTY` sentinel) was carried into row 56's prose instead. **Lesson:** `diagrams/` is flat and
  topic-scoped while rows are folder-scoped, so folder-based lane boundaries do not partition it.
  Assign the illustrator pass to exactly one lane per topic, separately from the writer rows.

- **A stray JDK source tree sits inside the notes folder and needs a human `rm`.**
  `src/notes/detailed/java-collections/java.base/java/util/{TreeMap,AbstractCollection,AbstractList,LinkedHashMap}.java`
  was created when a writer's `jar xf ... -C <dir>` silently ignored `-C`. It is not part of the note
  set. `rm` is denied to every agent in this pipeline, so it could not be cleaned up in-run. Writer
  packets were amended to forbid `jar xf` and to require the single-command form
  `unzip -o -q <src.zip> '<pattern>' -d /tmp/jc49src` instead.

- **Row 72c split on 2026-08-28, at planning time rather than after an overrun.** The row was
  specified as "5 puzzles **plus** the atomic concept checklist", and the two do not fit: the five
  INTERNALS puzzles are ~330 lines of compiled-and-run source plus 62 lines of transcript plus their
  explanations (784 lines with the required ending), and the checklist is 486 bullets (509 lines).
  Together they would have been ~1,270. Split at the artifact boundary:
  `92c-interview-internals-c-puzzles-and-checklist.md` (row 72c, 784 — the puzzles, leaves 5.1.40/41/47)
  and `92d-interview-internals-d-atomic-concept-checklist.md` (row 72d, 509 — leaf 5.3.8, the
  checklist alone). **`92c`'s filename is deliberately stale** — "and-checklist" now describes `92d` —
  and must NOT be renamed, per the precedent set by `hash-map/03b`, `hash-map/05b`/`05c`,
  `linked-hash-map/01b`/`01c` and `specialised-maps/03`. The split is also the better shape for the
  artifact: the checklist is the machine-readable surface downstream tooling parses, and a
  single-purpose file makes that parse unambiguous. `92d` is named `...interview-internals-d...` so
  that it matches the self-verify script's `9[012]-interview-*` exclusion, like its three siblings.
  Nav chain: `92b` → `92c` → `92d` → `93`.
- **Row 72 split again on 2026-08-28: `92-interview-internals.md` came back at 842 lines**, 42 past
  the 800 hard cap, even after the three-way pre-split below. Split at the concept boundary between
  the nine canonical `HashMap` questions (§5.1.1–5.1.9, which is what the row's leaves actually are)
  and the nine authored per-subject internals questions: `92-interview-internals.md` (row 72, 511 —
  keeps the tier summary table, D-151, Q&As 1–9) and
  `92a-interview-internals-a2-questions-10-18.md` (row 72a, 492 — Q&As 10–18, no leaves of its own).
  **Item 81's merge arithmetic was computed before splitting rather than after:** bodies 625 + a
  201-line mandated tail each gives 1,027 lines across two files against 842 in one, and neither
  child is thin (511 and 492, both above the ~350 floor), so this is not the gratuitous split item 65
  guards against. The alternative — a documented 42-line overage on item 80's precedent — was
  rejected because 42 is close enough to the ~50 boundary that the split is the cheaper defect, and
  unlike row 60b's 826 lines this file contains no single indivisible artifact (no class, no pinned
  harness) that a split would scatter. `92`'s title and intro were updated to say "questions 1–9",
  its cheat sheet keeps only the `HashMap` rows, and two self-tests that had moved subject (the
  `TreeMap` monomorphism one and the `AbstractMap.get` one) moved to `92a` and were replaced with two
  new `HashMap` ones. Nav chain: `91c` → `92` → `92a` → `92b` → `92c`.
- **Rows 70-73 PRE-SPLIT three ways each on 2026-08-28, before dispatch, per items 47/65/78.** Each interview row carries a summary table, 36 Q&As and 5 puzzles against a ~570-line estimate; every comparable row in this set overran its estimate by 2-3x, so these are planned as multi-file from the start rather than discovered at 1,200 lines. Shape per tier: `<N>` = summary table + Q&As 1-18, `<N>b` = Q&As 19-36, `<N>c` = the 5 puzzles (plus the atomic concept checklist in 72c). **Isolating the puzzles into their own file is deliberate** — item 77 requires every published expected output to be RUN in its published form, and a single-purpose file makes that gate tractable and re-runnable. Row 73 splits as trap index + version-stale table / drills / code-reading + schedule. Q&A count is 36 per tier from `10 + 2 x (18 - 5)`; the denominator is **18** subject folders, NOT the 19 that `ls` reports while the stray `java.base/` directory remains (item 79).

## File plan

| # | File | Subtopic | Tier | Leaves | Primary concepts | Diagrams | Est. lines | Status | Lines |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `framework/01-basics-why-and-hierarchy.md` | The framework itself | BASICS | 1.1.1–1.1.11, 1.2.1–1.2.20 | Why a framework at all; array covariance vs generics; the optional-operation bargain; the interface hierarchy; why `Map` is not a `Collection`; where `java.util.concurrent` grafts on | D-01, D-02, D-03, D-04, D-06 | 420 | done | 371 |
| 2 | `framework/02-interface-method-surfaces.md` | The framework itself | BASICS | 1.3.1–1.3.22 | The `Collection` surface; `toArray` and its two traps; the `Queue` throw-vs-null pairs; `Deque` as stack and as queue; `ListIterator`'s cursor; the `Map` surface | D-07, D-08, D-10 | 430 | done | 391 |
| 3 | `framework/03-catalogue-a-lists-and-sets.md` | The framework itself | BASICS | 1.4.1–1.4.13 | `ArrayList` vs `LinkedList` vs `Vector`/`Stack`; `CopyOnWriteArrayList`; the four hash/linked/tree/enum set families; `newSetFromMap` | none new | 380 | done | 513 |
| 4 | `framework/04-catalogue-b-maps.md` | The framework itself | BASICS | 1.4.14–1.4.24 | `HashMap`/`LinkedHashMap`/`TreeMap`; `Hashtable` and `Properties`; `EnumMap`; `IdentityHashMap` and `WeakHashMap`; the concurrent maps | none new | 370 | done | 289 |
| 5 | `framework/05-catalogue-c-queues-and-specials.md` | The framework itself | BASICS | 1.4.25–1.4.41 | `ArrayDeque` and `PriorityQueue`; the blocking-queue family; the lock-free queues; `BitSet`; the immutable families; the anti-catalogue | none new | 440 | done | 593 |
| 6 | `framework/06-matrices-and-choosing.md` | The framework itself | BASICS | 1.10.1–1.10.7, 2.14.1–2.14.10 | The null-policy matrix and why each class chose its policy; the thread-safety matrix; the ordering matrix; the choosing decision tree | D-27, D-63 | 400 | done | 560 |
| 7a | `framework/07-legacy-a-vector-stack-hashtable.md` | The framework itself | INTERMEDIATE | 2.15.1–2.15.9 | `Vector` and why it is not a thread-safe `ArrayList`; `Stack`'s 1-based `search` and bottom-up iteration; `Hashtable`/`Dictionary` mechanics; `Enumeration` vs `Iterator` | none new | 380 | done | 489 |
| 7b | `framework/07-legacy-b-version-history.md` | The framework itself | INTERMEDIATE | 3.16.1–3.16.17 | The release-by-release history; the three version traps; the removed/deprecated list; the cost of retrofitting old interfaces | D-141 | 400 | done | 517 |
| 8 | `framework/08-abstract-skeletons.md` | The framework itself | INTERNALS | 3.18.1–3.18.12 | The six skeletons and what each demands; why `AbstractList` on a linked structure is O(n²); `AbstractMap.get` is O(n); extend vs delegate | D-05, D-143, D-144 | 380 | done | 523 |
| 9 | `contracts/01-ordering.md` | Ordering contracts | BASICS | 1.6.1–1.6.15 | The `compareTo` contract; consistent-with-equals and who violates it; `Comparator` combinators and what `reversed()` reverses; never subtract to compare | D-13, D-14 | 400 | done | 595 |
| 10 | `contracts/02-equals-hashcode-contract.md` | Ordering contracts | BASICS | 1.7.1–1.7.11 | The `equals` contract; the `hashCode` contract; why unequal hashes strand an entry; the mutable-key trap; `getClass` vs `instanceof`; the `31` multiplier | D-15, D-16, D-17 | 420 | done | 475 |
| 11 | `contracts/03-equals-hashcode-jdk.md` | Ordering contracts | BASICS | 1.7.12–1.7.21 | `String.hashCode` and its cache; engineered `String` collisions; the JDK types' `hashCode`s; enum identity hashes; collection `equals`/`hashCode` across implementations | D-18, D-19, D-20 | 400 | done | 600 |
| 12 | `contracts/04-generics-and-boxing.md` | Ordering contracts | BASICS | 1.8.1–1.8.12 | Erasure and why `ArrayList` holds `Object[]`; heap pollution; the `Integer` cache; the boxing blow-up in bytes; unboxing NPE | D-21, D-22, D-23 | 400 | done | 540 |
| 13 | `contracts/05-wildcards-and-pecs.md` | Ordering contracts | INTERMEDIATE | 2.5.1–2.5.11 | PECS; why `addAll` takes `? extends E`; why `Comparator<? super T>`; unpacking `<T extends Comparable<? super T>>`; why `add` is barred on `List<? extends Number>` | D-40, D-41 | 380 | done | 458 |
| 14 | `iteration/01-basics-iteration.md` | Iteration | BASICS | 1.5.1–1.5.16 | Enhanced-for desugaring; the `Iterator` state machine; `Iterator.remove` cost per implementation; `removeIf`; the three ways to walk a `Map`; the four legal mutate-while-iterating strategies | D-09, D-11, D-12 | 430 | done | 600 |
| 15 | `iteration/02-fail-fast-fail-safe.md` | Iteration | INTERMEDIATE | 2.2.1–2.2.17 | `modCount` and `expectedModCount`; what counts as a structural modification; the second-to-last-element escape; snapshot iterators; weakly consistent iterators | D-30, D-31, D-32 | 440 | done | 599 |
| 16 | `iteration/03-internals-spliterator.md` | Iteration | INTERNALS | 3.13.1–3.13.16 | Why `Spliterator` exists; the `trySplit` contract; the eight characteristics; good splits vs bad splits; the parallel-stream decision rule; writing your own | D-123, D-124, D-125 | 440 | done | 600 |
| 17 | `sequenced-collections/01-sequenced-collections.md` | Sequenced collections (Java 21) | BASICS | 1.9.1–1.9.16 | The gap JEP 431 filled; the three interfaces and the retrofit map; `reversed()` as a write-through view; `addFirst` moving rather than duplicating; entry snapshots; the source-compatibility fallout | D-24, D-25, D-26 | 430 | done | 551 |
| 18 | `cost-and-memory/01-master-cost-table.md` | Cost and memory | INTERMEDIATE | 2.1.1–2.1.13 | The master cost table; amortised vs average vs worst; `containsValue` is always O(n); constant factors and the `ArrayList`/`LinkedList` crossover; `RandomAccess` as a runtime switch and the `Collections` thresholds | D-28, D-29 | 440 | done | 594 |
| 19 | `cost-and-memory/02-internals-memory-headers.md` | Cost and memory | INTERNALS | 3.15.1–3.15.12 | Object and array headers; compressed oops and the 32 GB cliff; boxing arithmetic; `HashMap.Node` at 32 bytes; 69 bytes to store 8; the node size ladder to `TreeNode` | D-137, D-138 | 420 | done | 515 |
| 20 | `cost-and-memory/03-internals-memory-collections.md` | Cost and memory | INTERNALS | 3.15.13–3.15.24 | Per-collection footprints; empty-collection cost; the map-of-empty-lists trap; measuring with JOL; compact object headers and Valhalla | D-139 | 400 | done | 350 |
| 21 | `cost-and-memory/04-observability.md` | Cost and memory | INTERNALS | 3.17.1–3.17.15 | The heap-dump workflow; MAT collection queries; diagnosing a bad `hashCode` vs over-allocation; debugger reading and the debugger-triggered CME; allocation profiling; always-on guards | D-142 | 420 | done | 502 |
| 22 | `array-list/01-internals-a-growth.md` | `ArrayList` | INTERNALS | 3.1.1–3.1.10 | `DEFAULT_CAPACITY = 10`; the two empty-array sentinels and array identity as a flag; `grow` and `ArraysSupport.newLength`; `SOFT_MAX_ARRAY_LENGTH`; the 1.5× sequence | D-64, D-65 | 400 | done | 586 |
| 23 | `array-list/02-internals-b-mutation.md` | `ArrayList` | INTERNALS | 3.1.11–3.1.21 | `add` and `add(int,E)` as one `arraycopy`; `fastRemove` and the trailing null; the null-split scan; `ensureCapacity`/`trimToSize`/`clear` | D-66, D-67 | 440 | done | 597 |
| 23b | `array-list/02b-internals-bulk-removal.md` | `ArrayList` | INTERNALS | 3.1.22, 3.1.23 | `removeIf`'s two-pass `long[]` deathRow bitset; `batchRemove`'s `catch` repair and `finally`; `shiftTailOverGap`; the `Collection.removeIf` default contrast | D-68 | 440 | done | 599 |
| 24 | `array-list/03-internals-c-views-and-iterators.md` | `ArrayList` | INTERNALS | 3.1.24–3.1.32 | `SubList`'s field wiring and `root.modCount`; `Itr`/`ListItr` state; `ArrayListSpliterator`; `RandomAccess`; the two array-size OOMEs; `Vector` and `CopyOnWriteArrayList` contrasts | D-69, D-70 | 400 | done | 505 |
| 25 | `array-list/04-amortised-analysis.md` | `ArrayList` | INTERNALS | 3.2.1–3.2.14 | Amortised is not average; the aggregate, accounting and potential methods; why 1.5× and not 2×; amortised O(1) does not mean predictable latency; `heapify` is O(n) | D-71, D-72, D-73 | 440 | done | 523 |
| 26 | `array-list/05-build-my-array-list.md` | `ArrayList` | INTERNALS | 4.1.1–4.1.6 | A complete generic `MyArrayList`; fields, growth and the core operations | D-145 | 480 | done | 600 |
| 26b | `array-list/06-build-my-array-list-b-iterators.md` | `ArrayList` | INTERNALS | 4.1.7–4.1.8 | The fail-fast `Itr` and `ListItr` | none new | 420 | done | 423 |
| 26c | `array-list/07-build-my-array-list-c-sublist-and-equality.md` | `ArrayList` | INTERNALS | 4.1.9–4.1.11 | The `SubList` view and structural equality | none new | 480 | done | 545 |
| 26d | `array-list/08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md` | `ArrayList` | INTERNALS | 4.1.12–4.1.13 | `removeIf` with bitset compaction; sorting in place | none new | 480 | done | 422 |
| 26e | `array-list/09-build-my-array-list-e-spliterator-diff-and-benchmark.md` | `ArrayList` | INTERNALS | 4.1.14–4.1.16 | The midpoint `Spliterator`; the diff vs the real `ArrayList`; the JMH harness (timings deliberately unpublished — Open questions item 13) | none new | 480 | done | 520 |
| 27 | `linked-list/01-internals.md` | `LinkedList` | INTERNALS | 3.3.1–3.3.12 | `Node` and the `first`/`last` fields; `node(int)`'s bidirectional shortcut; link/unlink pointer surgery and GC-help nulling; 24 bytes per node; why it loses even at mid-insert; poor spliterator splits | D-74, D-75, D-76 | 430 | done | 518 |
| 28 | `linked-list/02-build-my-linked-list.md` | `LinkedList` | INTERNALS | 4.2.1–4.2.4 | A complete generic `MyLinkedList`: nodes, pointer surgery and the `Deque` surface | none new | 420 | done | 600 |
| 28b | `linked-list/03-build-my-linked-list-b-iterators-and-benchmark.md` | `LinkedList` | INTERNALS | 4.2.5–4.2.8 | The `ListItr` with true O(1) cursor insert; `descendingIterator`; the diff vs the real `LinkedList`; the benchmark that settles mid-insert | none new | 420 | done | 497 |
| 29 | `array-deque/01-internals.md` | `ArrayDeque` | INTERNALS | 3.4.1–3.4.19 | The circular-buffer invariant and the reserved slot; the JDK 9 version trap; the `inc`/`dec`/`sub` helpers; capacity 17; `grow`'s jump and un-wrap slide; null prohibition as a consequence | D-77, D-78, D-79 | 450 | done | 565 |
| 30 | `array-deque/02-build-my-array-deque.md` | `ArrayDeque` | INTERNALS | 4.4.1, 4.4.2, 4.4.3, 4.4.5, 4.4.6 | A complete generic `MyArrayDeque` in both the power-of-two and the Java 21 helper style; the field set; the circular helpers; null rejection; the four primitives | none new (re-embeds D-78) | 420 | done | 600 |
| 30b | `array-deque/03-build-my-array-deque-b-grow-iterator-and-diff.md` | `ArrayDeque` | INTERNALS | 4.4.4, 4.4.7, 4.4.8 | `grow` with the un-wrap slide; the two-slice iterator and `delete`'s shift compensation; diff vs the real one | none new (re-embeds D-79) | 420 | done | 464 |
| 31 | `priority-queue/01-internals-a-heap.md` | `PriorityQueue` | INTERNALS | 3.5.1–3.5.10 | `DEFAULT_INITIAL_CAPACITY = 11`; the array↔tree index mapping; `siftUp` and its JIT-monomorphic split; `siftDown`'s smaller-child pick; `heapify` in O(n) and the constructor fast paths | D-80, D-81, D-82, D-83 | 450 | done | 563 |
| 31b | `priority-queue/01b-internals-removeat-and-iteration.md` | `PriorityQueue` | INTERNALS | 3.5.11, 3.5.12, 3.5.13 | `removeAt`'s moved-element return; the `forgetMeNot` deque; `indexOf`/`contains` as O(n); why iteration, `toString`, `stream` and `toArray` are heap order and not sorted | D-84 | 380 | done | 377 |
| 32 | `priority-queue/02-internals-b-traps.md` | `PriorityQueue` | INTERNALS | 3.5.14–3.5.20 | Mutating a priority in place; no stability and the sequence-number fix; max-heap and bounded top-k; `PriorityBlockingQueue`'s allocation spinlock; no `decreaseKey`; Fibonacci and pairing heaps | none new (D-84 moved to row 31b with leaf 3.5.11) | 380 | done | 506 |
| 33 | `priority-queue/03-build-my-priority-queue.md` | `PriorityQueue` | INTERNALS | 4.5.1, 4.5.2, 4.5.4, 4.5.5 | `MyPriorityQueue` fields and constructors; `grow`; both sifts in both variants; `heapify` | none new | 440 | done | 525 |
| 33b | `priority-queue/04-build-my-priority-queue-b-operations-and-iterator.md` | `PriorityQueue` | INTERNALS | 4.5.3, 4.5.6 | `offer`/`poll`/`peek`/`clear`; the linear-scan lookups; `removeAt` with the moved-element return; the `forgetMeNot` iterator | none new | 440 | done | 479 |
| 33c | `priority-queue/05-build-my-priority-queue-c-variants-and-diff.md` | `PriorityQueue` | INTERNALS | 4.5.7, 4.5.8, 4.5.9 | `StablePriorityQueue` via a private stamped wrapper; `BoundedTopK` on a min-heap; the diff vs the real one; the compile-and-run transcript | none new | 440 | done | 437 |
| 34 | `hash-map/01-internals-a-constants-and-hash.md` | `HashMap` | INTERNALS | 3.6.1–3.6.10 | The six constants as one designed set; the overloaded `threshold` field; `Node` and its four fields; the cached `hash` | D-85 | 420 | done | 572 |
| 34b | `hash-map/01b-internals-a2-hash-spread-and-sizing.md` | `HashMap` | INTERNALS | 3.6.11–3.6.16 | `hash()`'s single xor-shift; why spread at all — high-bit entropy; why one shift and not Java 7's four; `tableSizeFor`; power-of-two capacity as the reason the index is a mask | D-86, D-87, D-88 | 440 | done | 580 |
| 35 | `hash-map/02-internals-b-put-and-get.md` | `HashMap` | INTERNALS | 3.6.17–3.6.20 | `getNode`'s branch; the `==`-before-`equals` short-circuit; `putVal` control flow; the empty-bin fast path | D-89 | 480 | done | 594 |
| 35b | `hash-map/02b-internals-b2-bincount-and-treeifybin.md` | `HashMap` | INTERNALS | 3.6.21, 3.6.22 | `binCount` and the `>= TREEIFY_THRESHOLD - 1` off-by-one; `treeifyBin`'s capacity guard and why resize beats treeify below 64 | D-90 | 340 | done | 385 |
| 36 | `hash-map/03-internals-c-resize.md` | `HashMap` | INTERNALS | 3.6.23 | `resize()`'s four jobs; the `oldThr`/`newThr` capacity-and-threshold arithmetic; the `>= DEFAULT_INITIAL_CAPACITY` guard on threshold doubling; the `MAXIMUM_CAPACITY` terminal branch | none new (D-92, D-93 are in row 36a) | 300 | done | 339 |
| 36a | `hash-map/03a-internals-c1-lo-hi-split.md` | `HashMap` | INTERNALS | 3.6.24–3.6.26 | The transfer loop verbatim; the lo/hi split; why exactly one bit decides; order preservation, and why it is not an iteration-order guarantee | D-92, D-93 | 460 | done | 566 |
| 36b | `hash-map/03b-internals-c2-concurrent-resize-and-tree-split.md` | `HashMap` | INTERNALS | 3.6.27, 3.6.28 | The Java 7 concurrent-resize cycle, pointer write by pointer write; Java 8's quieter bug — lost entries, resurrected entries, the NPE, the torn `size` | D-94 (frames a–d), D-95 | 440 | done | 483 |
| 36c | `hash-map/03c-internals-c3-tree-split.md` | `HashMap` | INTERNALS | 3.6.29 | `TreeNode.split`'s lo/hi walk over the `next` overlay; the `lc <= UNTREEIFY_THRESHOLD` decision per half; `untreeify` and its three real call sites | none new | 320 | done | 413 |
| 37 | `hash-map/04-internals-d-treeify.md` | `HashMap` | INTERNALS | 3.6.30 | The `TreeNode` inheritance chain and what its bytes cost; the two-phase treeify (list first, then tree) and the `next` overlay that survives | D-91, D-96 | 400 | done | 537 |
| 37a | `hash-map/04a-internals-d1-puttreeval-and-comparable.md` | `HashMap` | INTERNALS | 3.6.31, 3.6.32 | `find`'s dual-subtree search; `putTreeVal`'s ordering ladder and the `tieBreakOrder` fallback; `comparableClassFor`'s reflective screen and what it rejects | none new | 460 | done | 600 |
| 37b | `hash-map/04b-internals-d2-poisson-and-hysteresis.md` | `HashMap` | INTERNALS | 3.6.33, 3.6.34 | The Poisson justification for load factor 0.75 and treeify threshold 8; why 6 for untreeify — the hysteresis band | D-97, D-98 | 420 | done | 486 |
| 37c | `hash-map/04c-internals-d3-collision-dos.md` | `HashMap` | INTERNALS | 3.6.35, 3.6.36 | Hash-collision DoS and CVE-2011-4858; why the JDK chose treeification over Java 7u6's randomised hashing | none new | 400 | done | 509 |
| 38 | `hash-map/05-internals-e-sizing-and-iteration.md` | `HashMap` | INTERNALS | 3.6.37–3.6.40 | The sizing arithmetic and why `new HashMap<>(n)` is the wrong call; `HashMap.newHashMap` and its three siblings; `putMapEntries` pre-sizing; non-default load factors | D-99 | 450 | done | 585 |
| 38a | `hash-map/05a-internals-e1-removal-and-iteration-order.md` | `HashMap` | INTERNALS | 3.6.41 | Removal never shrinks the table; `removeNode`, `reinitialize()` and `clear()`; a 10M-entry map still owns a 2^24 = 16,777,216-slot array after draining | none new | 380 | done | 471 |
| 38b | `hash-map/05a1-internals-e1b-iteration-order.md` | `HashMap` | INTERNALS | 3.6.42 | Iteration order is table order then bin order — and a treeified bin is headed by the current tree root via `moveRootToFront`, NOT insertion order (Open questions 20) | none new | 450 | done | 471 |
| 38c | `hash-map/05b-internals-e2-views-hooks-and-hashtable.md` | `HashMap` | INTERNALS | 3.6.43, 3.6.44, 3.6.45 | The cached `keySet`/`values`/`entrySet` views; the `afterNode*` hooks as the `LinkedHashMap` seam; `containsValue` walks the table | none new | 470 | done | 594 |
| 38d | `hash-map/05c-internals-e4-hashtable-and-prime-modulus.md` | `HashMap` | INTERNALS | 3.6.46, 3.6.47 | `Hashtable`'s `(oldCapacity << 1) + 1` growth and modulo indexing; "prime capacity" is folklore — only 6 of the first 15 are prime (Open questions 21) | none new | 440 | done | 441 |
| 39 | `hash-map/06-build-my-hash-map.md` | `HashMap` | INTERNALS | 4.3.1, 4.3.2 | `MyHashMap`'s class head and field set; `Node` with the cached hash; `spread` reproducing `h ^ (h >>> 16)`; `tableSizeFor` reproducing the `numberOfLeadingZeros` trick | none new | 430 | done | 431 |
| 39a | `hash-map/06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md` | `HashMap` | INTERNALS | 4.3.3 | Lazy table allocation with `threshold` as the pending capacity; the seven-member extension surface (`Node` visibility, `newNode`, `replacementNode`, the three `afterNode*` hooks, field visibility) that `MyLinkedHashMap` will need | D-146 (frames a–d) | 360 | done | 356 |
| 39b | `hash-map/07-build-my-hash-map-b-put-get-resize.md` | `HashMap` | INTERNALS | 4.3.4, 4.3.5, 4.3.6 | `put` with the empty-bin fast path, chain walk and `==`-before-`equals`; `get`/`containsKey`/`getOrDefault`/`remove`; `resize` with the lo/hi split preserving order | none new | 530 | done | 530 |
| 39c | `hash-map/08-build-my-hash-map-c-treeify-and-defaults.md` | `HashMap` | INTERNALS | 4.3.7, 4.3.8 | The `SortedBin` simplification and its screened-`Comparable` guard; `computeIfAbsent`/`merge`/`putIfAbsent`/`compute` with the mutated-during-mapping detection | none new | 580 | done | 584 |
| 39d | `hash-map/09-build-my-hash-map-d-views-and-iterator.md` | `HashMap` | INTERNALS | 4.3.9, 4.3.10 | `keySet`/`values`/`entrySet` as live views with working `remove`; `HashIterator` walking the table bin by bin, fail-fast | none new | 420 | done | 418 |
| 39e | `hash-map/10-build-my-hash-map-e-set-linked-and-diff.md` | `HashMap` | INTERNALS | 4.3.11, 4.3.12 | `MyHashSet` on the `PRESENT` dummy; `MyLinkedHashMap` with the `before`/`after` overlay, `accessOrder` and `removeEldestEntry`; a working `LruCache` | none new | 590 | done | 599 |
| 39f | `hash-map/10a-build-my-hash-map-f-the-demo-harness.md` | `HashMap` | INTERNALS | none new — the harness | `Demo.java` in full, producing every printed output quoted across rows 39–39e; the 200,000-operation differential test against `java.util.HashMap` | none new | 510 | done | 509 |
| 39g | `hash-map/10b-build-my-hash-map-g-diff-and-collision-dos.md` | `HashMap` | INTERNALS | 4.3.13, 4.3.14 | The diff table vs `java.util.HashMap`; the collision-DoS measurement with the sorted bin on and off, and against the JDK's own tree bin | D-147 | 380 | done | 377 |
| 40 | `linked-hash-map/01-internals.md` | `LinkedHashMap` | INTERNALS | 3.7.1, 3.7.2, 3.7.6 | The `before`/`after` overlay and its 8 bytes; the four `newNode`/`replacementNode`/`newTreeNode`/`replacementTreeNode` overrides; `linkNodeAtEnd` (JDK 21) vs `linkNodeLast` (JDK 8/17) | D-100 | 470 | done | 472 |
| 40a | `linked-hash-map/01a-internals-a2-hooks-and-access-order.md` | `LinkedHashMap` | INTERNALS | 3.7.4, 3.7.8 | `afterNodeAccess` and the access-relink surface; `get` relinks, `containsKey` does not, and `putIfAbsent`/`computeIfAbsent` on a present key DO — see Open questions 25, 26 | D-101 | 470 | done | 533 |
| 40b | `linked-hash-map/01a1-internals-a3-insertion-removal-and-containsvalue.md` | `LinkedHashMap` | INTERNALS | 3.7.3, 3.7.5, 3.7.7, 3.7.9 | `afterNodeInsertion` and `removeEldestEntry`; `afterNodeRemoval`; why `containsValue` is O(n) over the chain, not the table | none new | 470 | done | 442 |
| 40c | `linked-hash-map/01b-internals-b-lru-and-sequenced.md` | `LinkedHashMap` | INTERNALS | 3.7.10 | The ten-line LRU and its four bugs | none new | 470 | done | 519 |
| 40d | `linked-hash-map/01b1-internals-b2-access-order-is-a-write.md` | `LinkedHashMap` | INTERNALS | 3.7.11, 3.7.12 | Access order makes a read a structural write; the CME a plain `get` can throw | none new | 470 | done | 353 |
| 40e | `linked-hash-map/01c-internals-c-sequenced-and-caching.md` | `LinkedHashMap` | INTERNALS | 3.7.13, 3.7.14 | The Java 21 `SequencedMap` surface; `ReversedLinkedHashMapView` as a live view | none new | 470 | done | 565 |
| 40f | `linked-hash-map/01c1-internals-c2-memory-set-and-caffeine.md` | `LinkedHashMap` | INTERNALS | 3.7.15, 3.7.16, 3.7.17 | Per-entry memory vs `HashMap`; `LinkedHashSet` over the same overlay; why Caffeine is the real cache | none new | 470 | done | 361 |
| 41 | `linked-hash-map/02-build-lru-by-hand.md` | `LinkedHashMap` | INTERNALS | 4.6.2 (part 1 of 2) | `HashMap<K, Node>` plus a sentinel-terminated doubly-linked list; why the map's value is the node and not the value; the six-write unlink-relink; `put`'s three cases | D-148 | 560 | done | 599 |
| 41a | `linked-hash-map/02a-build-lru-b-proof-and-cost.md` | `LinkedHashMap` | INTERNALS | 4.6.2 (part 2 of 2) | The 300,000-operation property test against an access-order `LinkedHashMap`; the 64-versus-40 bytes-per-entry bill; when hand-rolling is actually the right call | none new | 520 | done | 520 |
| 41b | `linked-hash-map/03-build-lfu-sketch.md` | `LinkedHashMap` | INTERNALS | 4.6.3 (part 1 of 2) | Why frequency is a multiset where recency is a total order; the frequency-bucket `LfuCache`; the two `minFrequency` rules, the second proved by breaking it | none new | 560 | done | 583 |
| 41c | `linked-hash-map/03a-build-lfu-b-policy-comparison.md` | `LinkedHashMap` | INTERNALS | 4.6.3 (part 2 of 2) | LRU's scan vulnerability against LFU's pollution-by-history; the head-to-head transcript where the two evict different keys; aging, and W-TinyLFU as the production answer | none new | 340 | done | 325 |
| 42 | `tree-map/01-navigable-api.md` | `TreeMap` | INTERMEDIATE | 2.10.1–2.10.13 | The `floor`/`ceiling`/`lower`/`higher` table; inclusive-flag range views; time-series bucketing; interval lookup; the sliding-window rate limiter; leaderboards | D-56, D-57 | 440 | done | 388 |
| 43a | `tree-map/02-internals-a1-invariants-and-height.md` | `TreeMap` | INTERNALS | 3.8.1–3.8.3 | The five red-black invariants; the `h ≤ 2 log₂(n+1)` height bound, proved; why an unbalanced BST degenerates on sorted insertion | D-104 | 380 | done | 352 |
| 43b | `tree-map/02b-internals-a2-entry-and-rotations.md` | `TreeMap` | INTERNALS | 3.8.4, 3.8.5 | `Entry<K,V>`'s five fields; `rotateLeft`/`rotateRight` pointer surgery | D-105a, D-105b | 360 | done | 397 |
| 43c | `tree-map/02c-internals-a3-fixafterinsertion.md` | `TreeMap` | INTERNALS | 3.8.6 | `fixAfterInsertion`'s four cases: red uncle recolour, black uncle zigzag, black uncle straight, root forced black | D-106a, D-106b, D-106c, D-106d | 420 | done | 437 |
| 43d | `tree-map/02d-internals-a4-fixafterdeletion.md` | `TreeMap` | INTERNALS | 3.8.7 | `fixAfterDeletion`'s 4 logical cases mirrored left/right (rendered as 5 frames — see Substitutions) and the "double black" concept | D-107a, D-107b, D-107c, D-107d, D-107e | 480 | done | 462 |
| 43e | `tree-map/02e-internals-a5-deleteentry-and-successor.md` | `TreeMap` | INTERNALS | 3.8.8, 3.8.9 | `deleteEntry`'s successor-swap trick for two-child deletion; `successor`/`predecessor` and why in-order traversal is amortised O(1) per step | D-108 | 400 | done | 367 |
| 44a | `tree-map/03-internals-b1-key-identity-and-nulls.md` | `TreeMap` | INTERNALS | 3.8.10–3.8.14 | `getEntry` vs `getEntryUsingComparator`; `compare` routing and the `ClassCastException`; `compare == 0` is key identity, never `equals`; the `TreeSet.contains`/`equals` disagreement; null keys and the comparator escape hatch | none new | 420 | done | 543 |
| 44b1 | `tree-map/03b-internals-b2-buildfromsorted.md` | `TreeMap` | INTERNALS | 3.8.15 | `buildFromSorted`'s O(n) balanced construction | D-109a, D-109b, D-109c | 260 | done | 458 |
| 44b2 | `tree-map/03b2-internals-b2b-views-and-memory.md` | `TreeMap` | INTERNALS | 3.8.16, 3.8.17 | The `NavigableSubMap`/`AscendingSubMap`/`DescendingSubMap` range-view classes and `inRange`; 40 bytes per entry vs `HashMap`'s 32 | D-37, D-110 | 400 | done | 483 |
| 44c | `tree-map/03c-internals-b3-comparisons-and-alternatives.md` | `TreeMap` | INTERNALS | 3.8.18–3.8.23 | Why O(log n) carries a large constant; AVL vs red-black and why the JDK picked red-black; the B-tree contrast; `ConcurrentSkipListMap`'s probabilistic levels; why lock-free is easy on a skip list and hard on a red-black tree; `TreeSet` as a `TreeMap` wrapper | D-111 | 420 | done | 604 |
| 45a | `tree-map/04-build-my-tree-map.md` | `TreeMap` | INTERNALS | 4.6.1 (part 1 of 6) | `MyTreeMap` fields, `compare()`, `getEntry`, `rotateLeft`/`rotateRight`, `put` with `fixAfterInsertion` | none new (re-embeds none) | 480 | done | 614 |
| 45b1 | `tree-map/04b-build-my-tree-map-b-deletion.md` | `TreeMap` | INTERNALS | 4.6.1 (part 2 of 6) | `remove`/`successor`/`deleteEntry`'s successor swap; `fixAfterDeletion` cases A (sibling red) and B (sibling black, both children black) | none new | 380 | done | 382 |
| 45b2 | `tree-map/04b2-build-my-tree-map-b2-fixafterdeletion-cd-and-demo.md` | `TreeMap` | INTERNALS | 4.6.1 (part 3 of 6) | `fixAfterDeletion` cases C (near-red/far-black) and D (far-red, terminating) plus the left/right mirror; the deletion demo | none new | 380 | done | 490 |
| 45c1 | `tree-map/04c-build-my-tree-map-c-navigable-and-iterator.md` | `TreeMap` | INTERNALS | 4.6.1 (part 4 of 6) | `floorEntry`/`ceilingEntry`/`lowerEntry`/`higherEntry`/`firstEntry`/`lastEntry` | none new | 440 | done | 475 |
| 45c2 | `tree-map/04c2-build-my-tree-map-c2-iterator.md` | `TreeMap` | INTERNALS | 4.6.1 (part 5 of 6) | The fail-fast in-order `Iterator`; the `ConcurrentModificationException` demo | none new | 220 | done | 316 |
| 45d | `tree-map/04d-build-my-tree-map-d-diff-and-demo.md` | `TreeMap` | INTERNALS | 4.6.1 (part 6 of 6) | Diff vs `java.util.TreeMap` table; the compile-and-run demo transcript and md5 | none new | 380 | done | 402 |
| 46a | `sets/01-set-over-map.md` | Sets | INTERNALS | 3.9.1–3.9.5 | `HashSet`'s `PRESENT` dummy and `add`-as-`put`; the dummy-boolean constructor `LinkedHashSet` uses; every `HashMap` fact transferring; the memory you pay for an unused value field | D-112 | 400 | done | 524 |
| 46b | `sets/01b-set-over-map-siblings-and-exceptions.md` | Sets | INTERNALS | 3.9.6–3.9.9 | The set-over-map family (`Collections.newSetFromMap`, `TreeSet`, `ConcurrentSkipListSet`, `ConcurrentHashMap.newKeySet()`); who breaks the pattern (`CopyOnWriteArraySet`, `EnumSet`) | D-113 | 340 | done | 589 |
| 47a | `sets/02-set-algebra.md` | Sets | INTERMEDIATE | 2.12.1–2.12.3 | `containsAll`/`addAll`/`removeAll`/`retainAll` as set algebra; the O(n·m) `removeAll` trap; `AbstractSet.removeAll`'s size branch | D-59, D-60 | 400 | done | 428 |
| 47b | `sets/02b-set-algebra-traps-and-beyond.md` | Sets | INTERMEDIATE | 2.12.4–2.12.10 | `retainAll` on a `keySet` view; the immutable-collection `removeAll` short-circuit question; the mutable-element stranding bug; `disjoint`, symmetric difference, missing multiset semantics, `EnumSet` bulk ops | none new | 340 | done | 516 |
| 48 | `sets/03-bitset.md` | Sets | INTERMEDIATE | 2.9.17–2.9.20 | `BitSet` as a set of small ints; the word layout and `length`/`size`/`cardinality`; the immediate-allocation surprise; sieve and permission-mask uses; `RoaringBitmap` for sparse domains | D-55, D-140 | 380 | done | 268 |
| 49 | `specialised-maps/01-enum-collections.md` | Specialised maps and sets | INTERMEDIATE | 2.9.1–2.9.6 | `EnumMap`'s ordinal array and why no hashing; density as a cost; `RegularEnumSet` vs `JumboEnumSet`; bulk ops as single bitwise instructions; `EnumSet` is mutable | D-51 | 380 | done | 593 |
| 50 | `specialised-maps/02-internals-enum-map-set.md` | Specialised maps and sets | INTERNALS | 3.10.1–3.10.7 | `keyUniverse` via `SharedSecrets`; `maskNull`/`unmaskNull`; the reused `lastReturnedEntry`; `RegularEnumSet`'s single `long`; `complementOf` as `~elements & mask`; ordinal dependence; why enum-keyed `HashMap` is worse | D-114, D-115, D-116 | 450 | done | 800 |
| 50b | `specialised-maps/02b-internals-enum-set.md` | Specialised maps and sets | INTERNALS | 3.10.8–3.10.14 | `EnumSet.noneOf`'s Regular/Jumbo choice; `RegularEnumSet`'s single `long`; `complement()` as `elements &= -1L >>> -universe.length` (there is no `mask` field — Open questions 35); bulk ops as single bitwise instructions | D-116 | 450 | done | 770 |
| 51 | `specialised-maps/03-identity-and-weak.md` | Specialised maps and sets | INTERMEDIATE | 2.9.7–2.9.9 | `IdentityHashMap`'s deliberate contract violation and its sizing; `WeakHashMap`'s weak keys and `expungeStaleEntries`; the value-holds-key leak; interned keys never clearing; why it is not a cache; the reference ladder | D-52, D-53, D-54 | 440 | done | 522 |
| 51b | `specialised-maps/03b-weak-hash-map.md` | Specialised maps and sets | INTERMEDIATE | 2.9.10–2.9.14 | `WeakHashMap`'s weak keys and `expungeStaleEntries`; the value-holds-key leak; interned keys never clearing; why it is not a cache; the reference-strength ladder | D-53, D-54 | 460 | done | 672 |
| 51c | `specialised-maps/03c-legacy-maps-and-properties.md` | Specialised maps and sets | INTERMEDIATE | 2.9.15–2.9.16 | `Hashtable`'s capacity 11, `(oldCapacity << 1) + 1` growth and `(hash & 0x7FFFFFFF) % tab.length` modulo indexing; `Properties` and `stringPropertyNames()` as a filtered snapshot over the defaults chain | none new | 440 | done | 502 |
| 52 | `specialised-maps/04-internals-identity-weak.md` | Specialised maps and sets | INTERNALS | 3.11.1–3.11.3 | The flat interleaved table with no `Node` objects; the identity-hash scramble to an even index; linear probing via `nextKeyIndex` and the `closeDeletion` back-shift; the sizing constants and the "one null slot always" rule; the `NULL_KEY` sentinel; the documented `Map`-contract violation and its real use cases | D-117a, D-117b, D-117c | 450 | done | 763 |
| 52a | `specialised-maps/04a-internals-identity-sizing-and-uses.md` | Specialised maps and sets | INTERNALS | 3.11.4–3.11.7 | The sizing constants and the one-null-slot rule; `NULL_KEY`; the documented `equals`/`hashCode` contract violation and its asymmetry (Open questions 36); the legitimate use cases | none new | 450 | done | 800 |
| 52b | `specialised-maps/04b-internals-weak-hash-map.md` | Specialised maps and sets | INTERNALS | 3.11.8–3.11.14 | `Entry extends WeakReference<Object>` — the entry *is* the reference; the `ReferenceQueue` and `expungeStaleEntries`'s real call sites; the clearing sequence's arbitrary gap; the value-holds-key leak and its fix; keys that never clear; `ThreadLocalMap`'s same shape; `size()` with side effects | D-118 | 420 | done | 799 |
| 53 | `immutable-collections/01-views-copies-snapshots.md` | Immutability and views | INTERMEDIATE | 2.3.1–2.3.5 | View vs copy vs snapshot stated once; `subList` as a live offset window; the parent-modification CME; `subList(a,b).clear()` as range delete; the retention leak | D-33, D-34, D-35 | 440 | done | 598 |
| 53b | `immutable-collections/01b-map-views-and-arrays-aslist.md` | Immutability and views | INTERMEDIATE | 2.3.6–2.3.9 | The three `Map` views and what `remove` does through each; `entrySet()` yielding live `Node`s that stay dangerously live across a resize and after removal; `Values` having no `remove` override, so `AbstractCollection.remove`'s in-loop `return true` is the "one matching mapping" proof; `EntrySet` having no `toArray` override where `KeySet`/`Values` do | D-36 | 460 | done | 632 |
| 53c | `immutable-collections/01c-treemap-range-and-reversed-views.md` | Immutability and views | INTERMEDIATE | 2.3.10–2.3.11 | Range views throw only on out-of-range **write** — read and remove are silently no-ops, so `headMap(30).remove(99)` leaves key 99 alive; `descendingMap`/`descendingSet`/`reversed()`; `reversed() == descendingMap()` on `TreeMap` but double-descending is NOT identity, and `TreeSet.descendingSet()` does not cache | none new | 400 | done | 656 |
| 53d | `immutable-collections/01d-arrays-aslist.md` | Immutability and views | INTERMEDIATE | 2.3.12–2.3.13 | `Arrays$ArrayList` is fixed-**size**, not read-only — `set`, `sort` and `replaceAll` all write through to the caller's array; the `List<int[]>` varargs-binding trap and the `Arrays.stream(arr).boxed().toList()` fix | none new | 380 | done | 507 |
| 54 | `immutable-collections/02-immutable-factories.md` | Immutability and views | INTERMEDIATE | 2.3.14–2.3.16 | `List.of`'s 0/1/2-arm fast paths vs `listFromTrustedArray`/`listFromArray` and where the defensive copy is actually paid; unmodifiable view vs immutable copy; `copyOf`'s same-instance return and the two cases where it does NOT apply — an unmodifiable view, and a `ListN` with `allowNulls == true` as `Stream.toList()` returns | D-38 | 460 | done | 673 |
| 54a | `immutable-collections/02a-shallow-immutability-and-boundaries.md` | Immutability and views | INTERMEDIATE | 2.3.17–2.3.19 | Shallow vs deep immutability; defensive copying at API boundaries and the copy-vs-view decision rule; `singletonList` vs `List.of` — **neither is mutable via `set`** (syllabus 2.3.19 is wrong; see Open questions), the real differences being null acceptance and `SingletonList.sort` being a silent no-op where `List.of(...).sort` throws | none new | 460 | done | 598 |
| 54b | `immutable-collections/02b-entries-snapshots-and-stream-terminals.md` | Immutability and views | INTERMEDIATE | 2.3.20–2.3.24 | `Map.entry` vs `SimpleEntry` vs `Map.Entry.copyOf` (Java 17); `CopyOnWriteArrayList` snapshot iterators; `EnumSet.copyOf`/`clone`; the stream-terminal-op mutability matrix; the factory decision table | D-61 (table) | 420 | done | 693 |
| 55 | `immutable-collections/03-immutability-tiers.md` | Immutability and views | INTERMEDIATE | 2.4.1–2.4.5 | The five tiers, rung by rung; Tier 1 splitting in two because `Arrays.asList.set` is allowed and `Collections.nCopies.set` throws (Open questions — D-39 departure); `EnumSet` really sits at Tier 0; the seven-column comparison table | D-39 | 420 | done | 600 |
| 55a | `immutable-collections/03a-immutability-tiers-comparison-table.md` | Immutability and views | INTERMEDIATE | 2.4.6 | The operational matrix tabulating the finished ladder, its harness, and the `SALT32L` iteration-order proof (the salt drives the iterator only; `probe()` is unsalted `floorMod`) | none new | 450 | done | 459 |
| 55b | `immutable-collections/03b-immutability-tiers-b-factory-rules.md` | Immutability and views | INTERMEDIATE | 2.4.7–2.4.10 | `Set.of` duplicate-argument and `Map.of` duplicate-key rejection at construction; the 10-pair cap and `Map.ofEntries`; the 0–10 overloads; null hostility and where `contains(null)` throws vs returns false; `indexOf(null)` on `ListN`; Guava `Immutable*` | none new | 440 | done | 602 |
| 55c | `immutable-collections/03c-null-queries-and-guava.md` | Immutability and views | INTERMEDIATE | 2.4.11–2.4.13 | Null hostility — where it throws vs returns false; Guava `Immutable*` as the comparison point | none new | 450 | done | 647 |
| 56 | `immutable-collections/04-internals-immutable-collections.md` | Immutability and views | INTERNALS | 3.12.1–3.12.5 | The 0–10 `List.of` overloads and why they exist; `List12`'s `e0`/`e1` with the real `EMPTY` sentinel and `e1` typed `Object`; `ListN`'s `Object[] elements` and `allowNulls`; `listFromTrustedArray` vs `listFromArray`; `Set12`/`SetN` and `Map1`/`MapN` — and **there is no `Map2`**: two pairs go straight to `MapN` | D-121 | 460 | done | 795 |
| 56b | `immutable-collections/04b-internals-open-addressing-and-salt.md` | Immutability and views | INTERNALS | 3.12.6–3.12.8 | Open addressing with `EXPAND_FACTOR = 2` as a **correctness requirement, not a tuning knob** — at factor 1 `probe` would hang, not throw; `probe`'s `i` / `-(i+1)` return encoding; `MapN`'s interleaved table, `4n` cells = `2n` pair slots, and `MapN.probe`'s real `floorMod(h, table.length >> 1) << 1` arithmetic | D-119, D-120 | 470 | done | 690 |
| 56b2 | `immutable-collections/04b2-internals-salt-cds-and-null-hostility.md` | Immutability and views | INTERNALS | 3.12.9–3.12.12 | `SALT32L`/`REVERSE` from `System.nanoTime()` at class-init, consumed by **iterators only** — every usage site enumerated, and `REVERSE == true` walks *ascending*; per-JVM-run order proved over three JVMs; **leaf 3.12.11 is WRONG** — the CDS seed is `-Xshare:dump`-scoped for reproducible archive builds and does NOT pin runtime order; null hostility, where leniency never varies but the throw *site* does | none new | 600 | done | 704 |
| 56c | `immutable-collections/04c-internals-mutators-serialization-and-views.md` | Immutability and views | INTERNALS | 3.12.13–3.12.14 | `AbstractImmutableCollection`'s throwing mutators, and why the `removeIf`/`sort` **defaults** must be overridden too or immutability leaks; `writeReplace` to the `CollSer` proxy — a package-private **top-level** class, so `java.util.CollSer` not `ImmutableCollections$CollSer`; `readObject`'s `InvalidObjectException`, demonstrated reachable; a round-tripped `Set.of` re-shuffles under the *receiving* JVM's salt | D-122 | 470 | done | 713 |
| 56d | `immutable-collections/04d-internals-sublist-and-reversed-view.md` | Immutability and views | INTERNALS | 3.12.15–3.12.16 | Immutable `SubList` delegating to the root with an offset; `ReverseOrderListView` (Java 21) — `reversed().reversed() == source` is **true** for lists, matching `LinkedHashMap` and unlike `TreeMap.descendingMap()`; `subList` on a reversed view **silently loses `RandomAccess`**; the view's mutator wall short-circuits before reaching the base's | none new | 300 | done | 579 |
| 56e | `immutable-collections/04e-internals-layout-and-legacy-factories.md` | Immutability and views | INTERNALS | 3.12.17–3.12.18 | `List.of(a,b)` at 24 B with no array, against 48 B for `new ArrayList<>(List.of(a,b))` and 80 B for `new ArrayList<>()` plus two `add`s — two different expressions the manifest conflates; `emptyList`/`singletonList` today, where `Collections.emptyList().clear()` succeeds silently but `List.of().clear()` throws, and the honest answer is "neither is cheaper — choose on semantics"; `List12`'s `EMPTY` sentinel exists for `@Stable` constant folding, per the JDK's own comment at `ImmutableCollections.java:564-565` | none new | 300 | done | 606 |
| 57 | `concurrent-collections/01-thread-safety-and-wrappers.md` | Concurrent collections | INTERNALS | 3.14.1–3.14.6 | What "not thread-safe" actually costs; unsafe publication; the single-mutex wrappers; why iteration still needs your lock; why compound actions still race; the view-mutex question — **leaf 3.14.6 proved WRONG, the views DO share the outer mutex in both JDK 8 and 21 (Open questions 65)** | none new | 380 | done | 415 |
| 58 | `concurrent-collections/02-internals-chm-a.md` | Concurrent collections | INTERNALS | 3.14.7–3.14.12 | The six-field set; `sizeCtl`'s **real** encoding vs its stale JDK javadoc (Open questions 61 — leaf 3.14.8 reproduces the comment, not the code); `spread` and the reserved sign bit; the three special node hashes; `casTabAt` for an empty bin vs `synchronized (f)` on a populated one; `get` as volatile reads only | D-126, D-127, D-129 | 480 | done | 623 |
| 58b | `concurrent-collections/02b-internals-chm-a2-cooperative-resize.md` | Concurrent collections | INTERNALS | 3.14.13, 3.14.14 | `transfer`'s stride arithmetic and `MIN_TRANSFER_STRIDE = 16`; `transferIndex` claimed by CAS, walking downward; the `ForwardingNode` with `hash == MOVED` that readers follow into `nextTable`; `helpTransfer` making a blocked writer into an extra resizer; why the resize is cooperative rather than stop-the-world | D-128a, D-128b, D-128c, D-128d | 470 | done | 726 |
| 59 | `concurrent-collections/03-internals-chm-b.md` | Concurrent collections | INTERNALS | 3.14.15–3.14.19 | Striped counters, `sumCount()` and why `size()` is an estimate while `mappingCount()` is a `long`; `@Contended` and false sharing; `TreeBin`'s own `lockState` read-write lock, distinct from `HashMap`'s `TreeNode`; the atomic compound methods that hold the bin lock; the `computeIfAbsent` self-deadlock, demonstrated deterministically on one thread — **it is `IllegalStateException("Recursive update")`, not a deadlock; leaf 3.14.19 is imprecise (Open questions 66)** | D-130 | 480 | done | 635 |
| 59b | `concurrent-collections/03b-internals-chm-c-bulk-nulls-and-segments.md` | Concurrent collections | INTERNALS | 3.14.20–3.14.23 | The bulk `forEach`/`search`/`reduce` family and what `parallelismThreshold` actually gates; `newKeySet()` and `keySet(defaultValue)`; why null values are forbidden — `get` returning null must mean absent; Java 7's 16 `ReentrantLock` segments, `concurrencyLevel`, and why segment locking was abandoned — **`Segment` is still IN JDK 21 as a serialization stub at `:1380` (Open questions 67)** | D-131 | 460 | done | 800 |
| 60 | `concurrent-collections/04-copy-on-write.md` | Concurrent collections | INTERNALS | 3.14.24–3.14.26 | The `volatile Object[] array` write path under a **plain monitor, not a `ReentrantLock`** (item 10a; D-132 departs from the manifest); `addIfAbsent`; the `COWIterator` snapshot and why `iterator.remove` throws; the cost model and where the crossover falls; the listener-list use case it was designed for | D-132, D-133 | 460 | done | 770 |
| 60b | `concurrent-collections/04b-build-copy-on-write-by-hand.md` | Concurrent collections | INTERNALS | 3.14.36, 4.6.8 | A `CopyOnWriteList<E>` over `AtomicReference<Object[]>`, complete and runnable; the CAS-retry loop a lock does not need; when hand-rolled beats `CopyOnWriteArrayList` (whole-snapshot swap, multi-element atomic update); the pinned build harness | none new | 480 | done | 826 |
| 61 | `concurrent-collections/05-blocking-and-lock-free-queues.md` | Concurrent collections | INTERNALS | 3.14.27–3.14.30 | Backpressure and the `BlockingQueue` surface — the four-way throw/null/block/timeout matrix; one lock and two conditions vs `putLock`/`takeLock` with cascading signals; `SynchronousQueue`'s zero-capacity handoff, **rewritten over `LinkedTransferQueue` in JDK 21** (Open questions 62 — leaf 3.14.29 is version-stale); `DelayQueue`'s leader-follower | D-134, D-135 | 500 | done | 800 |
| 61b | `concurrent-collections/05b-lock-free-queues-and-choosing.md` | Concurrent collections | INTERNALS | 3.14.31–3.14.33 | Michael–Scott's lazy tail as `ConcurrentLinkedQueue` implements it — the `weakCompareAndSet` on `tail` that is allowed to fail and never retried, the self-linking unlink, and O(n) approximate `size()` against O(1) `isEmpty()`; `LinkedTransferQueue`'s dual queue and why `transfer` is the only JDK guarantee that a consumer received the element; `ConcurrentSkipListMap`'s `Node`/`Index` levels — **1-in-4 indexed at all, `p = 0.5` per level, not "p = 0.25" (Open questions 68)** — CAS insert, two-phase null-marked deletion, and weakly-consistent iterators that never throw CME | D-136a, D-136b, D-136c, D-136d | 500 | done | 766 |
| 61c | `concurrent-collections/05c-failure-catalogue-and-choosing.md` | Concurrent collections | INTERNALS | 3.14.34, 3.14.35, 3.14.37 | The unsafe-collection failure catalogue, each mode derived from the unguarded reads and writes rather than from a lucky race transcript — and the Java 7 `HashMap` infinite loop flagged as version-stale, since Java 8's tail insertion removed that specific cycle while leaving the map unsafe; the choosing table with a *why* and a *when this is the wrong answer* column; virtual threads, `synchronized` pinning on JDK 21 and its removal by JEP 491 in JDK 24 | none new | 460 | done | 279 |
| 62 | `utilities/01-collections-and-arrays.md` | Utility surfaces | INTERMEDIATE | 2.6.1–2.6.19, 2.7.1–2.7.6 | `binarySearch`'s return encoding and its silent-wrong case; `rotate` by three reversals; `nCopies` as one object; the wrapper families; `checkedCollection` as a debugging tool; the `Arrays` surface underneath | D-42, D-43a, D-43b, D-43c, D-43d, D-44 | 480 | done | 659 |
| 63 | `utilities/02-sorting-a-timsort.md` | Utility surfaces | INTERMEDIATE | 2.8.1–2.8.9 | `Collections.sort` delegating to `List.sort`; TimSort's run detection and `MIN_MERGE`; `minRunLength`; the merge-stack invariants; the de Gouw proof and the JDK's fix; "comparison method violates its general contract" | D-45a, D-45b, D-45c, D-46, D-47 | 450 | done | 536 |
| 64 | `utilities/03-sorting-b-primitives.md` | Utility surfaces | INTERMEDIATE | 2.8.10–2.8.19 | Dual-pivot quicksort's three regions; why the object/primitive split exists; the Java 14+ additions; adversarial input; stability demonstrated; the `TreeMap`/`PriorityQueue` alternatives; sorting a map by value | D-48a, D-48b, D-48c, D-49, D-50 | 450 | done | 361 |
| 65 | `utilities/04-map-default-methods.md` | Utility surfaces | INTERMEDIATE | 2.11.1–2.11.14 | `putIfAbsent`'s return value; the `computeIfAbsent` multimap idiom; null semantics that remove entries; `merge` for counters; the counter-idiom table; non-atomicity on `HashMap`; recursive `computeIfAbsent` | D-58 | 440 | done | 468 |
| 66 | `utilities/05-streams-and-collectors.md` | Utility surfaces | INTERMEDIATE | 2.13.1–2.13.16 | `stream()` built on `spliterator()`; the `Collectors.to*` family; `toMap`'s duplicate-key and null throws; `groupingBy` with downstreams; when a stream is the wrong tool; the boxing you just paid for | D-62a, D-62b, D-62c, D-62d | 450 | done | 618 |
| 67 | `utilities/06-serialization.md` | Utility surfaces | INTERMEDIATE | 2.16.1–2.16.9 | Which collections are `Serializable`; why `elementData` is `transient`; `HashMap.readObject` re-putting; the changed-`hashCode` trap; the comparator requirement; the `CollSer` proxy; the gadget-chain link | D-122 | 400 | done | 663 |
| 68 | `utilities/07-third-party.md` | Utility surfaces | INTERMEDIATE | 2.17.1–2.17.10 | Guava's four missing structures; Eclipse Collections' memory claim; fastutil for primitives; Caffeine as the real cache; Agrona/JCTools; the decision rule and the cost of the dependency | none new | 400 | done | 445 |
| 69 | `build-it/01-supporting-builds.md` | Build it | INTERNALS | 4.6.4–4.6.7, 4.6.9–4.6.11 | A fixed-capacity ring buffer; a `Multimap` with cleanup-on-empty; a `BiMap` and its invariant; an `IntArrayList` making boxing concrete; a custom `Spliterator` measured; a checked-list guard; a CME harness | D-149, D-150 | 520 | done | 763 |
| 70 | `90-interview-basics.md` | all subjects | BASICS | 5.1.10–5.1.12, 5.1.15, 5.1.16, 5.1.18 | Part summary table across all 18 subject folders; Q&As 1–18 with spoken-length model answers | none new | 520 | done | 575 |
| 70b | `90b-interview-basics-b-questions-19-36.md` | all subjects | BASICS | 5.1.23, 5.1.29, 5.1.30, 5.1.32 | Q&As 19–36 with spoken-length model answers | none new | 520 | done | 587 |
| 70c | `90c-interview-basics-c-puzzles.md` | all subjects | BASICS | 5.1.33, 5.1.39, 5.1.43, 5.1.48 | 5 predict-the-output puzzles — every expected output RUN in its published form (gate, item 77) | none new | 380 | done | 616 |
| 71 | `91-interview-intermediate.md` | all subjects | INTERMEDIATE | 5.1.13, 5.1.17, 5.1.22, 5.1.24–5.1.27 | Part summary table; Q&As 1–18 with spoken-length model answers | none new | 520 | done | 711 |
| 71b | `91b-interview-intermediate-b-questions-19-36.md` | all subjects | INTERMEDIATE | 5.1.31, 5.1.34–5.1.38, 5.1.42 | Q&As 19–36 with spoken-length model answers | none new | 520 | done | 734 |
| 71c | `91c-interview-intermediate-c-puzzles.md` | all subjects | INTERMEDIATE | 5.1.44–5.1.46, 5.1.49, 5.1.50 | 5 predict-the-output puzzles — every expected output RUN (gate, item 77) | none new | 380 | done | 771 |
| 72 | `92-interview-internals.md` | all subjects | INTERNALS | 5.1.1–5.1.9 | Tier summary table; Q&As 1–9, the nine canonical `HashMap` questions. Carries item 22's `Comparable` qualifier on every treeify/collision-DoS claim | D-151 | 520 | done | 513 |
| 72a | `92a-interview-internals-a2-questions-10-18.md` | all subjects | INTERNALS | none — second half of row 72's Q&A block | Q&As 10–18: one source-level question per remaining subject folder (`ArrayList.grow`, `ArrayDeque` without a size field, the two sift methods, `deleteEntry`, the `LinkedHashMap` seam, `trySplit`, `List.of` internals, the byte arithmetic, the `Abstract*` skeletons) | none new | 480 | done | 493 |
| 72b | `92b-interview-internals-b-questions-19-36.md` | all subjects | INTERNALS | 5.1.14, 5.1.19–5.1.21, 5.1.28 | Q&As 19–36 with spoken-length model answers | none new | 520 | done | 812 |
| 72c | `92c-interview-internals-c-puzzles-and-checklist.md` | all subjects | INTERNALS | 5.1.40, 5.1.41, 5.1.47 | 5 predict-the-output puzzles (RUN — gate, item 77). **Filename is deliberately stale** — the checklist moved to row 72d | none new | 480 | done | 784 |
| 72d | `92d-interview-internals-d-atomic-concept-checklist.md` | all subjects | INTERNALS | 5.3.8 | The flat atomic concept checklist — 486 bullets, one per concept, sorted by subject folder then by order of appearance; format pinned for downstream parsing | none new | 300 | done | 573 |
| 73 | `93-drills-and-traps.md` | all subjects | INTERNALS | 5.2.1–5.2.3 | The consolidated trap index and the version-stale claims table — built from the verified findings in `## Open questions`, not re-derived | D-152 (table) | 560 | done | 417 |
| 73b | `93b-drills.md` | all subjects | INTERNALS | 5.3.1–5.3.5 | The numbers, matrices, cost, which-one and mechanism drills | none new | 520 | done | 406 |
| 73c | `93c-code-reading-and-schedule.md` | all subjects | INTERNALS | 5.3.6, 5.3.7 | The code-reading drills and the spaced-repetition schedule | none new | 420 | done | 701 |

## Leaf ledger

Every one of the 901 leaves is owned by exactly one row above. The syllabus text itself
lives in the source prompt; this ledger records ownership by section and range so a resumed
run can reconstruct assignments without re-deriving them.

| Syllabus section | Leaves | Owning file(s) |
|---|---|---|
| §1.1 Why a collections framework exists | 1.1.1–1.1.11 (11) | row 1 |
| §1.2 The hierarchy, exactly | 1.2.1–1.2.20 (20) | row 1 |
| §1.3 Interface method surfaces | 1.3.1–1.3.22 (22) | row 2 |
| §1.4 Every concrete implementation | 1.4.1–1.4.13 (13) | row 3 |
| §1.4 (cont.) | 1.4.14–1.4.24 (11) | row 4 |
| §1.4 (cont.) | 1.4.25–1.4.41 (17) | row 5 |
| §1.5 Iteration | 1.5.1–1.5.16 (16) | row 14 |
| §1.6 Ordering | 1.6.1–1.6.15 (15) | row 9 |
| §1.7 The equals/hashCode contract | 1.7.1–1.7.11 (11) | row 10 |
| §1.7 (cont.) | 1.7.12–1.7.21 (10) | row 11 |
| §1.8 Generics and boxing | 1.8.1–1.8.12 (12) | row 12 |
| §1.9 Sequenced collections | 1.9.1–1.9.16 (16) | row 17 |
| §1.10 The two matrices | 1.10.1–1.10.7 (7) | row 6 |
| §2.1 The master cost table | 2.1.1–2.1.13 (13) | row 18 |
| §2.2 Fail-fast, fail-safe, weakly consistent | 2.2.1–2.2.17 (17) | row 15 |
| §2.3 Views, copies, snapshots | 2.3.1–2.3.13 (13) | row 53 |
| §2.3 (cont.) | 2.3.14–2.3.24 (11) | row 54 |
| §2.4 Immutability tiers | 2.4.1–2.4.13 (13) | row 55 |
| §2.5 Wildcards and PECS | 2.5.1–2.5.11 (11) | row 13 |
| §2.6 The `Collections` utility surface | 2.6.1–2.6.19 (19) | row 62 |
| §2.7 The `Arrays` utility surface | 2.7.1–2.7.6 (6) | row 62 |
| §2.8 Sorting, in depth | 2.8.1–2.8.9 (9) | row 63 |
| §2.8 (cont.) | 2.8.10–2.8.19 (10) | row 64 |
| §2.9 Specialised maps and sets | 2.9.1–2.9.6 (6) | row 49 |
| §2.9 (cont.) | 2.9.7–2.9.16 (10) | row 51 |
| §2.9 (cont.) | 2.9.17–2.9.20 (4) | row 48 |
| §2.10 `NavigableMap` in anger | 2.10.1–2.10.13 (13) | row 42 |
| §2.11 `Map` default methods | 2.11.1–2.11.14 (14) | row 65 |
| §2.12 Set algebra | 2.12.1–2.12.10 (10) | row 47 |
| §2.13 Collections and streams | 2.13.1–2.13.16 (16) | row 66 |
| §2.14 The choosing framework | 2.14.1–2.14.10 (10) | row 6 |
| §2.15 Legacy members | 2.15.1–2.15.9 (9) | row 7a |
| §2.16 Serialization | 2.16.1–2.16.9 (9) | row 67 |
| §2.17 Third-party collections | 2.17.1–2.17.10 (10) | row 68 |
| §3.1 `ArrayList` source walk | 3.1.1–3.1.10 (10) | row 22 |
| §3.1 (cont.) | 3.1.11–3.1.21 (11) | row 23 |
| §3.1 (cont.) | 3.1.22, 3.1.23 (2) | row 23b |
| §3.1 (cont.) | 3.1.24–3.1.32 (9) | row 24 |
| §3.2 Amortised analysis | 3.2.1–3.2.14 (14) | row 25 |
| §3.3 `LinkedList` source walk | 3.3.1–3.3.12 (12) | row 27 |
| §3.4 `ArrayDeque` source walk | 3.4.1–3.4.19 (19) | row 29 |
| §3.5 `PriorityQueue` source walk | 3.5.1–3.5.10 (10) | row 31 |
| §3.5 (cont.) | 3.5.11, 3.5.12, 3.5.13 (3) | row 31b |
| §3.5 (cont.) | 3.5.14–3.5.20 (7) | row 32 |
| §3.6 `HashMap` source walk | 3.6.1–3.6.10 (10) | row 34 |
| §3.6 (cont.) | 3.6.11–3.6.16 (6) | row 34b |
| §3.6 (cont.) | 3.6.17–3.6.20 (4) | row 35 |
| §3.6 (cont.) | 3.6.21, 3.6.22 (2) | row 35b |
| §3.6 (cont.) | 3.6.23 (1) | row 36 |
| §3.6 (cont.) | 3.6.24–3.6.26 (3) | row 36a |
| §3.6 (cont.) | 3.6.27, 3.6.28 (2) | row 36b |
| §3.6 (cont.) | 3.6.29 (1) | row 36c |
| §3.6 (cont.) | 3.6.30 (1) | row 37 |
| §3.6 (cont.) | 3.6.31, 3.6.32 (2) | row 37a |
| §3.6 (cont.) | 3.6.33, 3.6.34 (2) | row 37b |
| §3.6 (cont.) | 3.6.35, 3.6.36 (2) | row 37c |
| §3.6 (cont.) | 3.6.37–3.6.40 (4) | row 38 |
| §3.6 (cont.) | 3.6.41 (1) | row 38a |
| §3.6 (cont.) | 3.6.42 (1) | row 38b |
| §3.6 (cont.) | 3.6.43, 3.6.44, 3.6.45 (3) | row 38c |
| §3.6 (cont.) | 3.6.46, 3.6.47 (2) | row 38d |
| §3.7 `LinkedHashMap` source walk | 3.7.1, 3.7.2, 3.7.6 (3) | row 40 |
| §3.7 (cont.) | 3.7.4, 3.7.8 (2) | row 40a |
| §3.7 (cont.) | 3.7.3, 3.7.5, 3.7.7, 3.7.9 (4) | row 40b |
| §3.7 (cont.) | 3.7.10 (1) | row 40c |
| §3.7 (cont.) | 3.7.11, 3.7.12 (2) | row 40d |
| §3.7 (cont.) | 3.7.13, 3.7.14 (2) | row 40e |
| §3.7 (cont.) | 3.7.15, 3.7.16, 3.7.17 (3) | row 40f |
| §3.8 `TreeMap` and red-black trees | 3.8.1–3.8.3 (3) | row 43a |
| §3.8 (cont.) | 3.8.4, 3.8.5 (2) | row 43b |
| §3.8 (cont.) | 3.8.6 (1) | row 43c |
| §3.8 (cont.) | 3.8.7 (1) | row 43d |
| §3.8 (cont.) | 3.8.8, 3.8.9 (2) | row 43e |
| §3.8 (cont.) | 3.8.10–3.8.14 (5) | row 44a |
| §3.8 (cont.) | 3.8.15–3.8.17 (3) | row 44b |
| §3.8 (cont.) | 3.8.18–3.8.23 (6) | row 44c |
| §3.9 The Set-over-Map wrapper pattern | 3.9.1–3.9.9 (9) | row 46 |
| §3.10 `EnumMap`/`EnumSet` internals | 3.10.1–3.10.14 (14) | row 50 |
| §3.11 `IdentityHashMap`/`WeakHashMap` internals | 3.11.1–3.11.14 (14) | row 52 |
| §3.12 `ImmutableCollections` internals | 3.12.1–3.12.18 (18) | row 56 |
| §3.13 `Spliterator` and the stream bridge | 3.13.1–3.13.16 (16) | row 16 |
| §3.14 Concurrency behaviour | 3.14.1–3.14.6 (6) | row 57 |
| §3.14 (cont.) | 3.14.7–3.14.12 (6) | row 58 |
| §3.14 (cont.) | 3.14.13, 3.14.14 (2) | row 58b |
| §3.14 (cont.) | 3.14.15–3.14.19 (5) | row 59 |
| §3.14 (cont.) | 3.14.20–3.14.23 (4) | row 59b |
| §3.14 (cont.) | 3.14.24–3.14.26 (3) | row 60 |
| §3.14 (cont.) | 3.14.36 (1) | row 60b |
| §3.14 (cont.) | 3.14.27–3.14.30 (4) | row 61 |
| §3.14 (cont.) | 3.14.31–3.14.33 (3) | row 61b |
| §3.14 (cont.) | 3.14.34, 3.14.35, 3.14.37 (3) | row 61c |
| §3.15 Memory footprint arithmetic | 3.15.1–3.15.12 (12) | row 19 |
| §3.15 (cont.) | 3.15.13–3.15.24 (12) | row 20 |
| §3.16 Version history | 3.16.1–3.16.17 (17) | row 7b |
| §3.17 Observability | 3.17.1–3.17.15 (15) | row 21 |
| §3.18 Abstract skeletons | 3.18.1–3.18.12 (12) | row 8 |
| §4.1 `MyArrayList` | 4.1.1–4.1.6 (6) | row 26 |
| §4.1 (cont.) | 4.1.7, 4.1.8 (2) | row 26b |
| §4.1 (cont.) | 4.1.9–4.1.11 (3) | row 26c |
| §4.1 (cont.) | 4.1.12, 4.1.13 (2) | row 26d |
| §4.1 (cont.) | 4.1.14–4.1.16 (3) | row 26e |
| §4.2 `MyLinkedList` | 4.2.1–4.2.4 (4) | row 28 |
| §4.2 (cont.) | 4.2.5–4.2.8 (4) | row 28b |
| §4.3 `MyHashMap` | 4.3.1, 4.3.2 (2) | row 39 |
| §4.3 (cont.) | 4.3.3 (1) | row 39a |
| §4.3 (cont.) | 4.3.4, 4.3.5, 4.3.6 (3) | row 39b |
| §4.3 (cont.) | 4.3.7, 4.3.8 (2) | row 39c |
| §4.3 (cont.) | 4.3.9, 4.3.10 (2) | row 39d |
| §4.3 (cont.) | 4.3.11, 4.3.12 (2) | row 39e |
| §4.3 (cont.) | none — the demo harness | row 39f |
| §4.3 (cont.) | 4.3.13, 4.3.14 (2) | row 39g |
| §4.4 `MyArrayDeque` | 4.4.1, 4.4.2, 4.4.3, 4.4.5, 4.4.6 (5) | row 30 |
| §4.4 (cont.) | 4.4.4, 4.4.7, 4.4.8 (3) | row 30b |
| §4.5 `MyPriorityQueue` | 4.5.1, 4.5.2, 4.5.4, 4.5.5 (4) | row 33 |
| §4.5 (cont.) | 4.5.3, 4.5.6 (2) | row 33b |
| §4.5 (cont.) | 4.5.7, 4.5.8, 4.5.9 (3) | row 33c |
| §4.6 Supporting builds | 4.6.1 (1) | rows 45a, 45b1, 45b2, 45c1, 45c2, 45d (one leaf, six files — see Folds) |
| §4.6 (cont.) | 4.6.2 (1) | rows 41 + 41a (one leaf, one concept, split across two files — see `## Folds recorded`) |
| §4.6 (cont.) | 4.6.3 (1) | rows 41b + 41c (one leaf, one concept, split across two files — see `## Folds recorded`) |
| §4.6 (cont.) | 4.6.4–4.6.7, 4.6.9–4.6.11 (7) | row 69 |
| §4.6 (cont.) | 4.6.8 (1) | row 60b |
| §5.1 The 50 questions | 14 of 50 — BASICS tier | rows 70 (5.1.10–5.1.12, 5.1.15, 5.1.16, 5.1.18), 70b (5.1.23, 5.1.29, 5.1.30, 5.1.32), 70c (5.1.33, 5.1.39, 5.1.43, 5.1.48) |
| §5.1 (cont.) | 19 of 50 — INTERMEDIATE tier | rows 71 (5.1.13, 5.1.17, 5.1.22, 5.1.24–5.1.27), 71b (5.1.31, 5.1.34–5.1.38, 5.1.42), 71c (5.1.44–5.1.46, 5.1.49, 5.1.50) |
| §5.1 (cont.) | 17 of 50 — INTERNALS tier | rows 72 (5.1.1–5.1.9), 72b (5.1.14, 5.1.19–5.1.21, 5.1.28), 72c (5.1.40, 5.1.41, 5.1.47); row 72a carries no leaves |
| §5.2 The trap index | 5.2.1–5.2.3 (3) | row 73 |
| §5.3 Drills | 5.3.1–5.3.7 (7) | row 73 |
| §5.3 (cont.) | 5.3.8 atomic checklist (1) | row 72 |

**Total: 901 leaves, every one assigned.**

## Reading order — first pass

Build the model from nothing, in this order:

1. `framework/01` … `framework/06` — why the framework exists, the hierarchy, the catalogue,
   the matrices. Stop and memorise the null-policy and ordering matrices before going on.
2. `contracts/01` … `contracts/04` — ordering and `equals`/`hashCode` are load-bearing for
   everything hashed or sorted that follows. Do not skip.
3. `iteration/01`, `iteration/02` — the iterator protocol and `ConcurrentModificationException`.
4. `sequenced-collections/01` — the Java 21 tier, while the hierarchy is fresh.
5. `cost-and-memory/01` — the master cost table, as the reference you will keep returning to.
6. `array-list/01` … `array-list/04`, then `linked-list/01` — the simplest internals first,
   and the amortised argument that recurs everywhere.
7. `array-deque/01`, `priority-queue/01`, `priority-queue/02`.
8. `hash-map/01` … `hash-map/05` — the centre of the topic. Then `linked-hash-map/01`,
   `sets/01`.
9. `tree-map/01` … `tree-map/03`, then `specialised-maps/01` … `04`, `sets/02`, `sets/03`.
10. `immutable-collections/01` … `04`.
11. `utilities/01` … `07`, `contracts/05`, `iteration/03`.
12. `concurrent-collections/01` … `05`.
13. `cost-and-memory/02` … `04`, `framework/07`, `framework/08`.
14. The `build-it` and `*-build-*` files, in any order. Type them out; do not read them.
15. `90` → `91` → `92` → `93`.

## Reading order — night-before re-read

1. `93-drills-and-traps.md` first — the trap index and the numbers drill reload the most per
   minute of anything in the set.
2. `framework/06-matrices-and-choosing.md` — the three matrices and the decision tree.
3. `cost-and-memory/01-master-cost-table.md` — the cost table only; skip the prose.
4. `hash-map/01`, `hash-map/03`, `hash-map/04` — constants, the lo/hi split, treeify. These
   three carry more interview weight than the rest of the set combined.
5. The `## Cheat sheet` section of every file you are shaky on, and nothing else from it.
6. `92-interview-internals.md`, ending on the atomic concept checklist as a self-quiz.
7. `90` and `91` Q&As, read as answer shapes rather than as content.

## Diagram manifest

The compact assignment (which file embeds which `D-NN`) is the `Diagrams` column of the file
plan above. The verbatim manifest — id, title, syllabus leaf, type, and the full **must show**
contents — is in [`00-diagram-manifest.md`](00-diagram-manifest.md).

Eight manifest entries are `table`-type and are rendered as Markdown tables in the owning
note file rather than as SVG: **D-07, D-20, D-27, D-32, D-61, D-125, D-139, D-152.** The
remaining 144 are standalone SVGs in `diagrams/`.

### Substitutions

- **D-103's `reversed().reversed()` annotation is WRONG and the prose departs from it, 2026-08-28.**
  The SVG (`D-103-reversed-linkedhashmap-view.svg`) annotates double reversal as "a view of a view,
  two objects deep, not the original map returned by identity". The source says the opposite:
  `ReversedLinkedHashMapView.reversed()` is `return base;`
  (`java.base/java/util/LinkedHashMap.java`, JDK 21, line 1224), so `m.reversed().reversed() == m`
  is `true` and double reversal allocates nothing. Confirmed by reading the source and by running it.
  `linked-hash-map/01c-internals-c-sequenced-and-caching.md` states the correct fact at the embed
  point, quotes the source, and notes in one line that the diagram overstates the cost.
  **Do not "fix" the prose to match the picture** — the SVG should be re-cut. Everything else the
  diagram shows (the single `base` field, the swap table, the walk of `before` from `tail`) is correct.
  The error originated in the illustrator brief, not in the manifest, which is silent on the point.

- **D-107 rendered as 5 frames, not the manifest's 6, on 2026-08-28.** Verified against the
  actual structure of `java.util.TreeMap.fixAfterDeletion` (JDK 21): the method is a single
  `while` loop with one `if (x == leftOf(parentOf(x))) {...} else {...}` split, and both
  branches implement the *same* 4 logical cases (sibling red; sibling black with both children
  black; sibling black with near child red/far child black; sibling black with far child red,
  terminating) mirrored left/right — 4 logical cases × 2 mirrors = 8 code branches, not 6
  distinct cases. Rendered as `D-107a`–`D-107d` (the 4 canonical cases on the "x is left child"
  branch, in source order) plus `D-107e` (a dedicated mirror-explanation frame stating the
  right-side branch repeats the same 4 cases with left/right and `rotateLeft`/`rotateRight`
  swapped). All manifest must-show content is present across the 5 frames. The row-43d writer
  packet references `D-107a`..`D-107e`, not a 6-frame set.
- D-105 rendered as two files, `D-105a-rotate-left.svg` and `D-105b-rotate-right.svg`, matching
  the manifest's own "2 frames" instruction — not a departure, recorded here only so the row-43b
  writer packet uses the correct filenames.

## Open questions

Every `unverified` line returned by a writer is appended here.

44. **PROCESS LAW 2026-08-28 — a certifying artifact must be derived from the file's FINAL
    state, never from a pre-write computation.** Generalised from three separate incidents in
    this run, all the same shape:
    - A footer-patching regex ending `\s*$` consumed each file's trailing newline, silently
      shortening nine files by one line — so the freshly-written footers were "correct" for a
      length the files no longer had. Caught only because the script re-derived the count after
      writing and it disagreed with the number it had just written.
    - A build-it md5 was recorded from a run over a **patched** `/tmp` harness while the shipped
      notes still failed to compile (row 45, attempt 1). An md5 that holds only for a corrected
      copy reads as a guarantee and is worse than none.
    - Ten in-file footers drifted because they were patched correctly and the files were then
      edited again — patch-then-edit (see the `a footer is not write-once` rule).
    **Rules:** re-derive after writing and assert; when patching a line, match `[^\n]*` and
    assert the newline count is unchanged; any edit to a landed file re-patches that file's
    footer and re-checks its index row; a proof must run against the shipped files, never a
    fixed-up copy — if it needed fixing, fix the notes and re-run.

45. **TECHNIQUE 2026-08-28 — re-run every published program in its PUBLISHED form, not from the
    working copy. It catches a defect class nothing else does.** During the §3.11 re-split the
    writer re-executed each listing exactly as it appears on the page and found two files where
    the **listing and its own transcript disagreed**: a trimmed `Cap.java` no longer printed the
    table header its transcript showed, and `Probe.java` was missing a `println` that appears in
    its output. Both were invisible to reading, to compiling the working copy, and to any md5
    taken earlier — the code compiled fine, it just no longer produced the output printed beneath
    it. **A reader transcribing the page would get different output and conclude the notes are
    wrong.** This is the reader-facing analogue of item 44: the transcript is a certifying
    artifact and must be derived from the final published listing. Do this for every `[PROVE]`
    block before closing a row.

46. **RULE 2026-08-28 — label run-specific numbers as run-specific; claim the invariant, not the
    value.** Same row surfaced two. `IdentityHashMap.hashCode()` sums identity hashes, so it gave
    `1340971164` on one run and `490528984` on the next; the page now shows the re-run value and
    states that the load-bearing fact is only **that the two maps' hashes differ**, while the
    `106` alongside it is deterministic. Likewise the `null` key's slot: the claim is **"not slot
    0"**, not "slot 20". Compare item 21's `Hashtable` prime cut-off, which had to be restated as
    the value 6,143 rather than a step number after a table numbered from 0 made "step 9" read as
    wrong from outside. **Pattern: publish the property that holds across runs, and show a
    concrete transcript as an instance of it rather than as the claim.**

47. **POLICY 2026-08-28, superseding item 27's tier restriction — the 800 cap applies to EVERY
    row, and any row with 10+ leaves is PRE-SPLIT before dispatch.** Item 27 raised the cap for
    INTERNALS and build-it rows only. That was too narrow: three INTERMEDIATE rows overran 600 for
    exactly the same structurally-mandated reasons (row 51 at 1004, row 53b at 1291, row 54 at
    1030), and two more were published over 600 by orchestrator acceptance. Tier was never the
    variable — **`[SOURCE]` and `[PROVE]` leaf density is.** A quoted source line must also be
    explained, a proved claim needs a compiled program plus its real output, and the required
    ending is a fixed 150-215 lines whatever the tier.
    **Rules now:** 600 target, **800 hard cap, all tiers**; publish 600-800 when the excess is
    provably source quotes, runnable programs or the required ending, and justify it in the report;
    above 800, split; never compress mechanism; never scatter one method or class across files.
    **And the planning rule that actually removes the churn: any row with 10+ leaves is pre-split
    at leaf boundaries BEFORE a writer is dispatched.** Evidence across two lanes is unambiguous —
    every pre-split row landed inside the cap first time; every row not pre-split overran and had
    to be re-split, which cost hours and produced the mis-named children, the unrecorded rows and
    the 1300-line file this run has had to clean up.

48. **HUMAN ACTION OUTSTANDING 2026-08-28 — four stray JDK source files are inside the note
    tree.** A writer's `jar xf ... -C <dir>` silently ignored `-C` and extracted into the notes
    directory: `java.base/java/util/{TreeMap,AbstractCollection,AbstractList,LinkedHashMap}.java`,
    220 KB total. They are not part of the note set, have no index rows, and `rm` is denied to
    every agent, so **only a human can remove them.** Writers have been redirected to extract to
    `/tmp/jc*src/` instead. Note that the `java.base/java/util/X.java:NNN` strings throughout the
    notes are the canonical JDK citation form and refer to the JDK, **not** to these local copies
    — do not "repoint" them, and do not let an aggregate pass (rows 70-73) treat this directory as
    content. It contains no `.md` files, so the `done`-rows-vs-`.md`-files arithmetic in item 31
    is unaffected.

65. **STRUCTURAL 2026-08-28 — splitting is NOT free: every child file pays a full ~150-215 line
    tail, so over-splitting inflates the set and dilutes each file.** Quantified by the row-53b
    writer: the three mandated tail sections (`## Pitfalls`, `## Cheat sheet`, `## Self-test`) run
    about **200 lines per file on their own**, so a 2-leaf child "cannot reach 460 without them" —
    i.e. a 2-leaf file is roughly 200 lines of tail plus whatever mechanism it owns. Consequences
    that bound item 47's split-rather-than-compress rule:
    - **Splitting an N-line file in two does not give two N/2 files** — it gives roughly
      `N + 200` lines total. Splitting a 656-line file in two yields ~330 + ~320 **plus a second
      tail**, so the set grows and neither child is meaningfully lighter on mechanism.
    - Therefore **prefer accepting 600-800 over a split that would leave a child under ~350
      lines**, and never split a file whose overrun is smaller than the tail cost of the split.
    - Corollary for the observed pattern where trimmed files still overran: writers correctly
      trimmed only their own scaffolding (restating pitfalls, surplus self-tests, redundant
      cheat-sheet rows, nav paragraphs) — recovering 7-50 lines. That is the right *kind* of
      trim, but it can never close a 200-line gap, which is why the cap and not the trim had to
      move. **Trimming your own scaffolding is not compressing mechanism; the two must not be
      confused in either direction.**

66. **REQUIRED GATE 2026-08-28 — sweep relative links before closing any lane, and again
    before rows 70-73. A split renames files; cross-references do not follow.** Found by sweeping
    all `](../*.md)` and `](./*.md)` targets across the set: **7 dead links**, of which 6 point at
    rows not yet written (they resolve when those land) and **1 was genuine breakage** —
    `contracts/01-ordering.md` linked `../tree-map/03-internals-b-keys-and-views.md`, a path that
    stopped existing when `tree-map/` row 44 was split into `03-internals-b1-key-identity-and-nulls`,
    `03b-...`, `03b2-...` and `03c-...`. Repointed to `03-internals-b1-key-identity-and-nulls.md`,
    which owns the key-identity leaves (3.8.10-3.8.14) the sentence refers to. **This is the one
    defect class nothing else in the pipeline catches:** the index/disk arithmetic does not see it,
    footers do not see it, a compile-and-run proof does not see it, and the linking file usually
    belongs to a *different, already-closed* lane than the one that did the renaming. With ~25
    splits recorded and files deliberately keeping stale names, assume breakage rather than hoping.
    **Command (no `cd`, one call):**
    `for f in $(find . -name '*.md' -not -name '00-*'); do d=$(dirname "$f"); grep -oE '\]\(\.\.?/[^)]*\.md\)' "$f" | tr -d '])' | sed 's/^(//' | while read -r l; do [ -f "$d/$l" ] || echo "DEAD $f -> $l"; done; done`
    Classify every hit as *unwritten-row* (fine, list it) or *genuine* (fix it). Do not delete a
    reference to make the sweep pass — repoint it to the file that now owns the content.

67. **VERIFIED 2026-08-28 — leaf 3.14.19 is wrong, and the truth is a better answer. A recursive
    `computeIfAbsent` on ConcurrentHashMap does NOT deadlock on one thread — it THROWS.** Run on
    JDK 21, single thread:
    - **Same key (same reserved bin):** `m.computeIfAbsent("k", k -> m.computeIfAbsent("k", ...))`
      -> `java.lang.IllegalStateException: Recursive update`. Process exits 0; nothing blocks.
    - **Different key (different bin):** returns normally — `m.computeIfAbsent("alpha", k -> {
      m.put("beta","2"); return "1"; })` gives `1` with map `{alpha=1, beta=2}`. It **succeeds and
      is still a javadoc-contract violation**, i.e. a latent bug that happens to work.
    - **Genuine two-thread deadlock** is constructible but not deterministically demonstrable.
    Mechanism: `computeIfAbsent` on an empty bin installs a `ReservationNode` (hash
    `RESERVED = -3`, declared `ConcurrentHashMap.java:593`) and holds its monitor; a re-entrant
    call landing on a *reserved* bin is detected and thrown. There are **9** `"Recursive update"`
    throw sites (`:1063`, `:1167`, `:1742`, `:1763` among them). **The bit the folklore misses:
    `synchronized` is reentrant, which is exactly why the single-thread case cannot self-block** —
    so "it deadlocks" is wrong for the case people actually demonstrate.

68. **VERIFIED 2026-08-28 — leaf 3.14.6's warning is unfounded: `synchronizedMap` views DO share
    the outer mutex.** The leaf claims `synchronizedMap(...).keySet()` "is not synchronized on the
    same mutex in all JDK versions — check before relying on it." Checked in both trees:
    `Collections.SynchronizedMap.keySet()` / `values()` / `entrySet()` each pass the **identical
    outer `mutex` field** into the derived view's constructor —
    `keySet = new SynchronizedSet<>(m.keySet(), mutex)` — at JDK 21 `Collections.java:2912-2934`
    and JDK 8u202 `:2604-2623`. No divergence between 8 and 21. The real caveats are unchanged and
    are the ones to teach: iterating a synchronized view still requires holding the mutex yourself,
    and compound actions still race. Caveat recorded honestly by the writer: pre-Java-5 source was
    not available, so an older divergence cannot be ruled out — but it is irrelevant to a Java 21
    reader.

69. **CORRECTION to item 63 — D-132 does NOT contain the amber JDK-8 version-trap box. Row 60's
    writer must add it.** Item 63 describes intent, not the file. There is exactly **one** D-132 on
    disk, `D-132-cow-write-path.svg`, and grepping it for `ReentrantLock`, `version trap` and
    `JDK 8` returns **nothing**. Either the second version was overwritten at the same slug or it
    was never authored. The substance is safe — the SVG draws the plain `Object` monitor correctly,
    which is the load-bearing fact (index item 10a) — but the version-trap annotation a reader
    needs is absent. **Do not rely on item 63's description of any SVG's contents without grepping
    the file.** General lesson: a finding that asserts what a *diagram* contains is unverifiable
    from prose and must be checked against the SVG, exactly as a source citation is checked against
    the source.

70. **DUPLICATE SVG ARBITRATION — 13 manifest ids have two files each; canonical decided by what is
    EMBEDDED, not by which lane authored it.** Two lanes each ran an illustrator pass over
    `concurrent-collections/`' diagrams before a lane collision was discovered (item 64). Both
    members of every pair are source-verified and correct; this is redundancy, not error. 199 SVGs
    on disk where the manifest defines 152 ids.
    **CANONICAL (embedded by a note file — keep):** `D-126-chm-bin-level-concurrency.svg`,
    `D-127-spread-and-reserved-sign-bit.svg`, `D-128a-chm-transfer-strides.svg`,
    `D-128b-chm-forwardingnode-installed.svg`, `D-128c-chm-reader-follows-forwarding.svg`,
    `D-128d-chm-helptransfer.svg`, `D-130-chm-striped-counters.svg`.
    **ORPHANED (embedded by nothing — delete):** `D-126-chm-bin-concurrency.svg`,
    `D-127-spread-reserved-sign-bit.svg`, `D-128a-resize-frame1-setup.svg`,
    `D-128b-resize-frame2-migrate.svg`, `D-128c-resize-frame3-reader.svg`,
    `D-128d-resize-frame4-helptransfer.svg`, `D-130-size-striped-counters.svg`.
    **UNDECIDED until their rows are written** — 6 pairs, one of each becomes an orphan:
    **D-121** (row 56 — embed `D-121-listof-vs-arraylist-memory.svg` per item 64, so
    `D-121-list12-vs-arraylist-bytes.svg` becomes the orphan), **D-133** (row 60), **D-136a-d**
    (row 61). Whoever writes those rows must embed exactly one per id and name the loser here.
    **Test to use, not attribution:** for each `D-NN-*.svg`, grep the note tree for its basename;
    the embedded one is canonical. Attribution is unreliable because same-slug writes overwrite.

71. **PROCESS 2026-08-28 — assign the `diagrams/` illustrator pass to exactly ONE lane per folder,
    separately from the writer rows. Folder-based lane boundaries do not partition diagrams.**
    This is the structural cause of item 70, and it is worth fixing rather than re-arbitrating. Rows
    are folder-scoped; `diagrams/` is **flat and topic-scoped**, so two lanes working different
    folders can still collide in the one shared directory — and they did, burning two illustrator
    passes on the same 13 ids. It is the only artefact class in this pipeline where the lane
    boundary that works for `.md` files does not work at all. **Rule: when dispatching lanes, name
    the diagram owner per folder explicitly, and have every other lane embed-only — check
    `diagrams/` first and author nothing that already exists.**

72. **AUDIT FLAW 2026-08-28 — an exact-literal grep produced a FALSE NEGATIVE and nearly caused
    duplicated content. Audits must match the family, not the literal.** A lane audit grepped for
    the exact string `**Pitfall:**` to find files missing an inline marker, and reported `01d-arrays-aslist.md`
    as having none. It had two — written in a leaf-tagged variant, `**Pitfall (§2.3.12):**`, which
    the literal does not match. A writer was dispatched to "add the missing markers"; had it added
    rather than relocated, the file would have carried four near-identical warnings in ~120 lines.
    Its writer caught this and pushed back instead of complying, which is the behaviour that saved
    it. **Census across the set settles the canonical form: 107 files use bare `**Pitfall:**`, 1
    uses the tagged variant** — so bare is canonical and `01d` is the outlier to normalise.
    **Rules:** (a) audit with a family pattern — `grep -cE '\*\*Pitfall( \(§[0-9.]+\))?:\*\*'`
    — never the bare literal; (b) a false negative in an audit is more dangerous than a false
    positive, because it commissions work that damages a correct file; (c) when an audit says a
    file lacks something, the writer should verify the absence before adding.

73. **OVER CAP — `concurrent-collections/04b-build-copy-on-write-by-hand.md` is 907 lines** against
    the 800 hard cap (item 47), and its footer reads **559** against a real `wc -l` of 907, so it is
    also the largest footer drift seen in this run. It is row 60b, the §4.6.8 build-it. Needs a
    split at a leaf boundary plus a footer patched from final state, and its build proof re-pinned
    across whatever files result (item 28: blocks included per label, blocks excluded and the rule,
    block ORDER, what the digest covers, exact command lines). Also outstanding in the same lane:
    `immutable-collections/04b-internals-open-addressing-and-salt.md` (690) and
    `04b2-internals-salt-cds-and-null-hostility.md` (704) both carry `**Lines:** 0` placeholders.

74. **PLANNING LAW 2026-08-28, evidence-backed — 6 leaves is the ceiling for a row carrying
    `[SOURCE]`/`[PROVE]` tags; 8 for INTERMEDIATE. This governs rows 70-73 and any future topic.**
    Rows 49-56 were planned as 8 rows and landed as **26 files**: eleven of fourteen dispatched
    rows overran (1004, 1030, 1128, 1223, 1251, 1291, 669, 789, 879, 1300). **Pre-splitting helped
    but did not solve it** — rows 56/56b/56c were deliberately pre-split three ways on the evidence
    of 49-55 and **two of the three still overran** (1128, 1223). The measured rule: **every row at
    or under 6 leaves landed inside cap first time; every row above 8 overran without exception.**
    Cause is specific and predictable: in these sections the JDK classes are *small*, so a
    `[SOURCE]` obligation means quoting a **whole method** rather than excerpting a large one, and
    every `[PROVE]` needs a compiled program, its real transcript, and a paragraph bounding what
    the transcript establishes. **Roughly half a finished file here is inside fences.** Combined
    with item 65 (each child pays a ~150-215 line tail), the planning shape is: split to <=6 leaves
    per child, and do not split further even if a child overruns to 800.

75. **VERIFIED 2026-08-28 by running them — four `Collections`-vs-`List.of` facts, all confirmed.**
    Spot-checked the most surprising claims from rows 53-56 rather than banking them on report:
    - `Collections.emptyList() == List.of()` is **false** — different objects.
    - `Collections.emptyList().clear()` **succeeds silently**; `List.of().clear()` throws
      `UnsupportedOperationException`. Same emptiness, opposite mutator contracts.
    - **There is no `Map2`.** `Map.of(k1,v1,k2,v2).getClass()` is **`MapN`**; `Map1` covers exactly
      one pair. (Contrast `List12`, which really does cover one *and* two elements.)
    - **`TreeMap` range views throw only on out-of-range WRITE — read and remove are silent
      no-ops, and that is the dangerous half.** Measured: with keys 10 and 99,
      `headMap(30).remove(99)` returns **`null` and leaves key 99 alive in the source map**,
      `headMap(30).get(99)` returns `null`, but `headMap(30).put(99, ...)` throws
      `IllegalArgumentException`. A caller who trusts `remove` to report failure silently keeps
      the entry. The syllabus documents only the throwing half.

76. **VERIFIED 2026-08-28 — `List12`'s `EMPTY` sentinel is documented by the JDK, and the `Set12`
    copy of the comment carries a typo. Quote both uncorrected.** Closes the `@Stable` question:
    - `ImmutableCollections.java:564-565` — `// Use EMPTY as a sentinel for an unused element: not
      using null` / `// enables constant folding optimizations over single-element lists`.
    - `:791-793` — the same comment copied into `Set12`, reading **`enable`** (singular) and
      **`sets`**. A genuine typo in JDK source; quote it as written and do not silently fix it.
    - Fields: `@Stable private final E e0;` and `@Stable private final Object e1;` at **`:556-560`**
      — note line 555 is blank, so a `:555-559` citation is off by one. Class is
      `@jdk.internal.ValueBased` at `:552`; `size()` is `e1 != EMPTY ? 2 : 1` at `:575`; 18
      `@Stable` annotations in the file, counted by grep.
    **Process point this proved:** the writer **re-derived** these citations from source rather than
    transcribing the ones handed to it, and that is exactly how the off-by-one and the typo were
    caught. A relayed citation is an unverified citation — check it against the file even when it
    comes from the orchestrator. (Same lesson as item 41, where five line numbers were withdrawn as
    unverified and turned out correct: relay is not verification in either direction.)

77. **GATE for rows 70-73 — every predict-the-output puzzle and every model answer containing a
    transcript must be RUN in its published form before the row is closed. Not a habit; a gate.**
    Across this run, re-running published listings exactly as printed caught more defects than any
    structural check: an imagined `Map1`-vs-`MapN` value, two files whose listing no longer produced
    the transcript beneath it, a run-specific `identityHashCode` sum published as a constant, and a
    reproduction recipe that did not reproduce (`false`/`false` where the page claimed
    `false`/`true`). **Rows 70-73 are the highest-risk rows in the set for this**, because their
    content is disproportionately transcript: 5 predict-the-output puzzles per interview file plus
    model answers that quote behaviour. A wrong expected output in a predict-the-output puzzle is
    worse than a wrong sentence — the reader runs it, gets a different answer, and cannot tell
    whether they or the notes are wrong. **Procedure:** extract each puzzle's code exactly as
    published, compile with JDK 21 `-Xlint:all`, run, and diff against the printed expected output;
    where behaviour is unspecified or run-varying (identity hashes, `SALT32L` iteration order,
    `HashMap` order), publish the invariant and mark the transcript as one instance (items 46, 75).

78. **PLANNING SUMMARY for rows 70-73 — items 47 and 65 only work as a PAIR, and this is the shape
    to plan by.** From the lane that produced 26 files out of 8 planned rows: pre-splitting above
    ~6 `[SOURCE]`/`[PROVE]` leaves removed the churn, and item 65's ~350-line floor is what stopped
    pre-splitting from overshooting into thin files. Eleven of fourteen rows overran *before* the
    pair was in force; every row planned under it landed in cap first time. Measured cost of a
    split, from a §3.12 case: **1128 -> 1394 lines, +266 purely from the second file's mandated
    tail.** So: **split above ~6 tagged leaves; refuse any split leaving a child under ~350 lines;
    accept 600-800 rather than make a thin child.** Rows 70-73 carry 36 Q&As plus 5 puzzles each —
    plan them as multi-file from the start rather than discovering it at 1,200 lines.

79. **The stray `java.base/` directory CORRUPTS a structural count rows 70-73 depend on — a
    second, concrete reason it must be deleted (item 48).** This file's Layout section states
    **18 subject folders**, and the per-tier interview Q&A count is derived from it:
    `10 + 2 x (18 - 5) = 36` Q&As per interview file. But `ls -d */` now returns **19** non-diagram
    directories, because a writer's `jar xf ... -C` extracted `java.base/java/util/*.java` into the
    note tree. A writer of rows 70-73 that counts folders to derive the Q&A target gets
    `10 + 2 x (19 - 5) = 38` and writes two extra Q&As per file, or worse, notices the mismatch and
    "corrects" the Layout section. **Correct count: 18** — verified by excluding `diagrams/` and
    `java.base/`. Until a human removes it, any folder-derived arithmetic in this pipeline must
    exclude `java.base` explicitly. This is not cosmetic tidying; it is a wrong denominator sitting
    in the tree.

80. **DOCUMENTED CAP EXCEPTION 2026-08-28 — `concurrent-collections/04b-build-copy-on-write-by-hand.md`
    accepted at 826 lines, 26 over the 800 cap. Item 65 governs, and it says accept.** The file came
    down 907 -> 905 -> 854 -> 826 across four passes, losing only scaffolding. I had instructed a
    split at its 3.14.36 / 4.6.8 seam; **I am overriding my own instruction, because the rule
    postdates it and points the other way.** Item 65: *never split when the overrun is smaller than
    the tail cost of the split.* The overrun is **26 lines**; a split adds a full second ending,
    measured elsewhere in this set at **+266 lines** for one §3.12 split. Splitting here would grow
    the set by an order of magnitude more than the overrun it fixes, move the build-it away from the
    cost model that sets it up, and force the pinned harness to be re-derived across a new boundary
    for no reader benefit. **Its proof is sound and was re-derived from scratch, not carried:** the
    four labelled blocks were extracted from the shipped page into a clean directory, compiled and
    run, giving digest `1ef5f083139dd90dd5f6b9446f17bb6b` over 9 lines of stdout — identical to the
    earlier run, so it is a final-state digest and not a stale one (item 44). Both Pitfalls blocks
    were regex-tested to confirm they open with bare code and so cannot match the
    `// (\w+\.java)` inclusion rule. Footer verified at 826 against a live `wc -l`.
    **Precedent: a cap is a target with a documented exception process, not a number to shave
    toward across four passes.** When an overrun is under ~50 lines and the content is provably
    mandated, accept it and record why — that is cheaper than the churn, and the churn itself
    produced the mis-named children and stale footers this run has had to clean up.

81. **REFINEMENT to item 65 — the ~350-line child floor YIELDS to the 800 cap. Compute the merge
    before rejecting a split.** Row 61b split into `05b` (766) and `05c` (**254**), below item 65's
    floor, so this looked like the split that rule exists to prevent. **Measuring reversed the
    conclusion.** Bodies are 624 and 131; mandated tails are 142 and 123. Merging gives
    `624 + 131 + one tail (142)` = **897 lines, 97 over the cap** — a worse violation than a thin
    child, and far worse than the 26-line exception accepted for `04b` (item 80). **So the split is
    correct** and `05c` stands, with roughly half its length in required sections.
    **Rule, stated properly:** when a child would fall under ~350 lines, do not reject the split
    reflexively — compute `sum(bodies) + one tail` first. Reject the split only if that merged total
    is inside 800, or over it by less than ~50. Above that, a thin child is the lesser defect.
    Item 65's floor guards against *gratuitous* splitting; it is not a licence to blow the cap.

82. **FINAL DELETION MANIFEST — 13 orphaned SVGs + 1 stray directory. Requires a human; `rm` is
    denied to every agent.** All 13 duplicate manifest ids are now settled, decided by **what the
    written rows actually embed** (item 70's test) rather than by attribution. Every listed file is
    embedded by nothing and has no index row. Both members of each pair are source-verified and
    correct — this is redundancy from two lanes running illustrator passes over the same flat
    `diagrams/` folder (item 71), not error.
    **DELETE these 13 (canonical twin kept in each case):**
    `D-121-list12-vs-arraylist-bytes.svg` (keep `D-121-listof-vs-arraylist-memory.svg`),
    `D-126-chm-bin-concurrency.svg`, `D-127-spread-reserved-sign-bit.svg`,
    `D-128a-resize-frame1-setup.svg`, `D-128b-resize-frame2-migrate.svg`,
    `D-128c-resize-frame3-reader.svg`, `D-128d-resize-frame4-helptransfer.svg`,
    `D-130-size-striped-counters.svg`, `D-133-cow-cost-model.svg` (keep `D-133-cow-crossover.svg`),
    `D-136a-msqueue-frame1.svg`, `D-136b-msqueue-frame2.svg`, `D-136c-msqueue-frame3.svg`,
    `D-136d-msqueue-frame4.svg`.
    **DELETE this directory:** `java.base/java/util/` (4 JDK source files, 220 KB) — item 48, and it
    corrupts the 18-subject-folder denominator per item 79.
    **Verification after deletion:** `ls diagrams | wc -l` should read **186**, and
    `ls -d */ | grep -v diagrams | wc -l` should read **18**. Every `D-NN` embedded by a note file
    must still resolve — re-run the dead-link sweep in item 66.

83. **CLOSED — D-132's missing amber box is cosmetic; row 60's PROSE carries the version trap in
    full.** Item 69 flagged that `D-132-cow-write-path.svg` contains no `ReentrantLock` / `JDK 8` /
    `version trap` string, and it still does not. But `concurrent-collections/04-copy-on-write.md`
    handles it better than a diagram box could: a dedicated section headed *'The write path — a
    plain monitor, not a `ReentrantLock`'*, the JDK's own justifying comment quoted in full at
    `:105-107`, an explicit `**Version trap:**` callout naming the pre-2018 literature, and the
    JDK 8 declaration `final transient ReentrantLock lock = new ReentrantLock();` shown for
    contrast. **No reader of that page can miss it.** Leaving the SVG as-is: the diagram draws the
    JDK 21 mechanism correctly, and re-cutting it to add an annotation the prose already makes
    load-bearing is not worth the edit. Not a defect; not on the deletion list.
    **SUPERSEDED 2026-08-28 — the SVG was re-cut anyway, and the reason matters more than the box.**
    Investigating the duplicate-SVG arbitration (item 70) revealed *why* the annotation was absent:
    **two illustrator passes wrote `D-132-cow-write-path.svg` at the same slug, and the second
    silently overwrote the first.** The first pass's version *did* carry the amber box — item 63
    described a file that existed and had since been replaced, so item 69's "described intent, not
    the file" diagnosis was itself wrong. The same overwrite hit **`D-129-sizectl-states.svg`**, and
    there the damage was **not** cosmetic: the surviving version showed the resize state as **`-2`**,
    the stale-javadoc value, directly **contradicting item 61 and the prose of
    `02-internals-chm-a.md`, which is the page that embeds it.** A diagram that contradicts its own
    page is a real defect. Both files were rewritten and verified by grep: D-129 now carries
    `-2145714174` (twice), `32795`, `numberOfLeadingZeros`, the javadoc citation `:792-799` in a red
    "what the field javadoc says" box beside the real value in green, and **zero** occurrences of the
    wrong `2145517…` figure; D-132 now carries `version trap` (4), `ReentrantLock` (5) and `JDK 8`
    (3) alongside the correctly-drawn plain `Object` monitor. Both pass the full hygiene set —
    `viewBox` with no fixed width, no font under 11px, no `<style>`/`@import`, no pure black/white
    fill, and valid XML under `xml.dom.minidom`.
    **The transferable lesson, which is why item 71's one-illustrator-per-folder rule matters:** when
    two lanes write the same slug there is **no conflict and no evidence** — the loser is simply
    gone, and a later grep of "the file" describes whichever version won. So a same-slug collision
    is strictly more dangerous than a different-slug duplicate, because the different-slug case
    leaves 13 visible orphans to arbitrate while the same-slug case leaves nothing to notice. Any
    finding that asserts what a diagram *contains* must be re-grepped after any illustrator pass,
    not just once when written.

106. **MILESTONE 2026-08-28 — content rows 1-69 COMPLETE and fully verified. Baseline for rows
    70-73c.** Full sweep, every check run rather than asserted:
    - **145 `done` rows, 0 index/disk line-count mismatches.**
    - **0 footer problems** — every file's `**Lines:**` equals its real `wc -l`.
    - **2 files without a row**, exactly the two deliberately-retained SUPERSEDED drafts (item 31).
      The arithmetic gate holds: 147 `.md` files minus 145 rows = 2.
    - **0 inline `<svg>`, 0 missing trailing newlines, 0 broken `../diagrams/` references.**
    - **1 dead relative link**, `build-it/01-supporting-builds.md -> ../90-interview-basics.md`,
      which is row 70 and resolves when it lands. Re-run item 66's sweep after 70-73c.
    - **2 files over the 800 cap**: `concurrent-collections/04b` at 826 (documented exception,
      item 80) and the 1069-line superseded draft. Nothing else.
    - **147 files, 79,698 lines, 199 SVGs, 94 recorded findings.**
    All 901 syllabus leaves owned exactly once. Every `[SOURCE]`-tagged claim carries a file+line
    citation; every build-it row carries a behaviour-preserving digest with a pinned harness.
    **Ten wrong syllabus leaves and four wrong/corrupted diagram entries were caught by
    verification during this run — none by reading alone.**

107. **FIXED 2026-08-28 — `ConcurrentSkipListMap` was wrong in 7 places in a CLOSED lane's file;
    corrected by me since that lane had stood down.** `tree-map/03c-internals-b3-comparisons-and-alternatives.md`
    claimed an `Index`/**`HeadIndex`** overlay at **`p = 0.25`**. Both halves are wrong for JDK 21,
    verified against `java.base/java/util/concurrent/ConcurrentSkipListMap.java`:
    - **`HeadIndex` does not exist** — `grep` returns **zero** hits. It was removed in the skip-list
      rewrite; only `Index` remains (`:374`), and the top level is reached via the `head` field.
      Citing `HeadIndex` is a pre-rewrite version trap.
    - **The parameters are `k = 1, p = 0.5`**, hardwired, per the class comment at **`:248`**
      ("see method `doPut`"). `p = 0.25` conflates the parameter with its *outcome*: the same
      comment says those parameters "mean that about **one-quarter of the nodes have indices**. Of
      those that do, half have one level, a quarter have two, and so on", up to 62 levels. So
      one-quarter is the fraction of nodes indexed at all; 0.5 is the per-level continuation
      probability.
    Fixed in all 7 locations — prose, a diagram alt-text, a boxed definition, the cheat sheet and a
    self-test answer — each now stating the correction explicitly rather than silently. Footer
    re-patched (604) and the index row reconciled.
    **Process point: this was found by a LATER lane noticing a contradiction with its own sources,
    after the owning lane had closed.** A closed lane is not a verified lane. Cross-lane
    contradictions are worth chasing to the end of the run, and whoever finds one after the owner
    has gone should report it upward rather than assume it is already known.

108. **FIXED 2026-08-28 — `array-list/09` contradicted `linked-list/01` on `LinkedList`'s
    spliterator, and `array-list/09` was wrong.** Its cheat sheet read "`LinkedList` by contrast |
    `SIZED` but not `SUBSIZED`". Measured on JDK 21.0.7:
    `new LinkedList<>(...).spliterator()` reports **`ORDERED SIZED SUBSIZED`** — `SUBSIZED=true`,
    matching `LLSpliterator.characteristics()` at `LinkedList.java:1271` and matching
    `linked-list/01-internals.md`'s own cheat sheet, which had it right. Corrected in place, with
    the real distinction stated: **`SUBSIZED` is a promise about knowing sizes, not about the split
    being cheap.** `LinkedList`'s split is still O(n) because `trySplit` copies a prefix with
    `BATCH_UNIT = 1024`, growing per call, capped at `MAX_BATCH = 1 << 25`. Footer and index row
    reconciled (520).
    **Also measured and worth carrying into rows 72/73:** `List.of(1,2,3).spliterator()` reports
    **`IMMUTABLE=false`** — `AbstractImmutableList` never overrides `spliterator()`, so the default
    supplies `ORDERED` and the framework adds `SIZED | SUBSIZED`; **the immutability the class
    actually has is never advertised.** A good interview question, and the opposite of what a
    reader would guess.
    **This is the second cross-lane contradiction found after the owning lane closed** (item 107
    was the first). Both were caught by a later lane noticing its own sources disagreed with a
    written page. Two independent files stating incompatible facts is a defect class no per-file
    check can see — only a reader crossing folders finds it. **Rows 70-73, which read across all 18
    folders, are the only pass positioned to catch these; treat every disagreement they surface as
    real until source settles it.**

109. **REFINEMENT to item 22 — treeification is UNCONDITIONAL; only its BENEFIT depends on
    `Comparable`. There are now three wrong statements to guard against, not one.** Verified from
    source: **`treeifyBin` contains no `Comparable` check at all** — it tests only
    `MIN_TREEIFY_CAPACITY` (resizing instead if the table is too small) and then calls `treeify`.
    `comparableClassFor` is used **only** inside the tree operations, at `HashMap.java:2033`,
    `:2093` and `:2147` — i.e. in `find`/`putTreeVal` ordering, never in the decision to treeify.
    Corroborated by measurement: first `TreeNode` appears at entry 11 in a default-sized map,
    entry 9 when pre-sized to 64, **and at entry 9 for non-`Comparable` keys too.**
    **So all three of these are wrong:**
    (a) "treeification bounds collision attacks at O(n log n)" — false unqualified (item 22);
    (b) "treeification does not happen for non-`Comparable` keys" — **also false**, it happens at
        exactly the same thresholds;
    (c) "so `Comparable` makes no difference" — false; it is the whole difference.
    **Correct statement:** the bin treeifies regardless. With `Comparable` keys the tree gives a
    real total order and lookup is O(log n) (2.06 ms for 20,000 collisions). Without it,
    `putTreeVal` falls back to `tieBreakOrder` — class name then `identityHashCode` — which is not
    a total order over the keys, so `TreeNode.find` must search **both** subtrees: 529 ms, worse
    than the 312 ms plain chain. **You pay the tree's memory and complexity and get less than
    nothing.** This is the sharpest available form of the finding and belongs in rows 72 and 73.

110. **VERIFIED 2026-08-28 — the set's idealised "69 bytes per entry" understates a real 1M-entry
    `HashMap`; the honest figure is ~72 B, and the gap is power-of-two rounding.** For n = 1,000,000:
    `ceil(1M / 0.75) = 1,333,333`, and `tableSizeFor` rounds that up to **2^21 = 2,097,152 slots** —
    **2.10 slots per entry, not 1.33**, an 8.0 MB array under compressed oops. So per-entry cost is
    ~72 B against the idealised 69 B. **Publish both with the reason**, as the row-72 writer did:
    the array's share depends on where `n` sits relative to a power of two, so the per-entry figure
    is a band, not a constant. Worst case is just after a resize (2.0 slots/entry ->
    ~1.33 at the load-factor boundary).

111. **GATE RESULT for rows 70-73c, and the hole item 77 does not cover: an UNRUNNABLE fence is
    never gated.** The item-77 gate was applied mechanically to every published program in the four
    aggregate lanes — an extractor pulls each `java` fence whose first line full-matches
    `// <Name>.java` **from the shipped page**, compiles it with JDK 21.0.7 `-Xlint:all`, runs it,
    and diffs stdout against the plain fence published beneath it inside the same `<details>`.
    **20 programs, 19 byte-identical on the first or second attempt, 1 deliberately not** (see item
    112). Two real defects were caught by the diff rather than by reading: a transcript missing a
    trailing blank line that the program does print, and a trailing space after the last
    `forEachOrdered` element — both invisible to a human reader and both a difference a reader
    transcribing the page would hit.
    **But the gate only sees fences that are whole programs.** Two of this lane's own published
    *fragments* — a `LruCache extends LinkedHashMap` snippet and a generic `Comparator` composition —
    **did not compile**, and neither could ever have reached the extractor, because neither has a
    `main` or a `// X.java` label. `super(HashMap.newHashMap(maxEntries), 0.75f, true)` passes a map
    where an `int` capacity is required, and
    `Comparator.comparing(Stamped::value, byPriority).thenComparingLong(Stamped::seq)` cannot infer
    without explicit witnesses. Both were found only by extracting **every** `java` fence, wrapping
    each in the minimum scaffolding, and compiling it separately.
    **Rule to add to item 77: compile every fenced `java` block, not only the labelled runnable
    ones.** A class fragment is exactly the shape a reader copies into an IDE, and it is the shape
    the existing gate is blind to.

112. **TECHNIQUE 2026-08-28 — how to publish a genuinely non-deterministic transcript so that a
    future gate run does not read as a failure.** `92c`'s puzzle 5 prints `Set.of` iteration order,
    which is salted per JVM start (item 75), so it cannot be byte-identical across runs and must not
    be. Rather than drop the line — it is the teaching point — or leave a gate that fails
    intermittently, the page does four things, and this is the shape to reuse:
    (a) the program's own label says `Set.of order (VARIES per run)`, so the reader is warned in the
    output itself, not only in the prose;
    (b) the **next printed line is the invariant** — `immutable.stream().sorted().toList()` — so the
    stable fact sits beside the unstable one;
    (c) the file's header states which single line is non-deterministic and why;
    (d) the run was repeated **three** times and diffed **line by line**, establishing that
    **exactly one line** differs — three distinct orders (`[f,e,d,c,b,a]`, `[a,b,c,d,e,f]`,
    `[b,c,d,e,f,a]`) with all thirteen other lines byte-identical.
    That last step is what converts "this transcript is unreliable" into "this transcript is
    reliable except at line 8, proven". Without it, a later verifier has no way to tell a salted
    line from a real regression.

113. **STRUCTURAL — rows 70-73c landed as 14 files, not 12, and both extra splits were decided by
    computing item 81's merge arithmetic BEFORE splitting rather than after.** Row 72 came back at
    842 (42 over) and split into `92` (511, the nine `HashMap` questions and D-151) plus `92a` (492,
    the nine per-subject questions): bodies 625 + a 201-line mandated tail each = 1,027 lines across
    two files against 842 in one, with neither child under the ~350 floor. Row 72c was specified as
    "5 puzzles **plus** the checklist", which is 784 + 573 = ~1,360, and split at the artifact
    boundary into `92c` and `92d`. **Row 72b was NOT split** — it is 812, 12 over, and item 80's
    reasoning applies directly: a split would buy a second ~200-line tail to fix 12 lines.
    **The generalisable number from this lane: an aggregate row's mandated tail is ~200 lines and
    its cheat sheet alone runs 40-65 rows**, so a file that reads across all 18 folders starts at
    ~250 lines before any content. Plan aggregate rows at 18 Q&As per file, not 36 — the 36-per-tier
    count is right, the one-file-per-18 assumption was not.

114. **ACTION for whoever maintains `verify.sh` — two of its hard-coded checks are now stale, and
    one of them will report a false failure.** The script in this index's
    `## Self-verify before reporting done` section contains
    `grep -q '## Atomic concept checklist' "$ROOT/92-interview-internals.md"`. The checklist is leaf
    5.3.8 and, since the row-72c split, it lives in
    **`92d-interview-internals-d-atomic-concept-checklist.md`** — so that check now fails against a
    correct set. The right form is to search for the heading across the tree rather than in one named
    file: `grep -rql '^## Atomic concept checklist' "$ROOT" --include='9*.md'`, and assert exactly one
    hit. Second, the required-sections loop excludes `*9[012]-interview-*`, which by luck still covers
    all five INTERNALS files (`92`, `92a`, `92b`, `92c`, `92d` — the last was named
    `92d-interview-internals-d-...` **specifically** so it would match) but does **not** cover the
    `93*` series. Those three files were written with `## Pitfalls`, `## Cheat sheet`, `## Self-test`
    and 5 `<details>` each anyway, so the check passes on content; the exclusion pattern is simply
    describing the set less accurately than it thinks. Neither is a defect in the notes — both are
    the script drifting behind a filename, which is the same class of problem as item 66's dead
    links.

115. **FIXED 2026-08-28 — a NUL byte in `92b-interview-internals-b-questions-19-36.md` made it a
    BINARY file and silently disabled every text check on it. This is the most dangerous defect
    class found in the run, because it makes verification lie by omission.**
    `file` reported the page as `data`, not text, so `grep` treated it as binary and returned
    **nothing at all** — not a mismatch, *nothing*. My footer sweep read that empty result as
    "no footer found" while `tail` plainly showed `**Lines:** 812` two lines from the end. Every
    grep-based check in this pipeline — footers, inline `<svg>`, emoji, elisions, `TODO`, dead
    links, `**Pitfall:**` markers, leaf-coverage extraction — would have skipped this file in
    silence. A lane self-report of "0 drift" was accurate for every file grep could read.
    **Cause:** prose discussing strings whose `hashCode()` is genuinely 0 (the empty string, and
    `"\u0000"`) had a **literal NUL control byte** written where the two-character escape was
    meant. The claim is correct — both hash to 0, which is why `String` cannot use `hash == 0` as
    a "not yet computed" sentinel without the `hashIsZero` flag. Only the encoding was wrong.
    **Fix:** replaced the raw byte with the literal escape `\u0000`; line count unchanged, footer
    and index row still 812, file now reports `Unicode text, UTF-8 text`.
    **Gate to add — cheap, and it must run BEFORE any grep-based check:**
    `for x in $(find . -name '*.md'); do file -b "$x" | grep -q text || echo "NOT TEXT: $x"; done`
    Verified across all 161 files: **1 offender, now 0.** A checker that can be silently switched
    off by its input is worse than no checker, because it reports success.

> **Numbering rule — read before appending.** Item numbers in this list are unique and are cited
> by number from note prose and from writer briefs, so **never reuse a number and never renumber
> an existing item.** Append with the next free number; if you cannot see the whole list, append
> with a number well past the end rather than guessing. On 2026-08-28 three lanes appended
> independently and produced two items each numbered 16, 17 and 18; the later duplicates were
> renumbered to **39-43** (the earliest occurrence of each number kept its id, and no note prose
> referenced the moved ones, so nothing broke). The `### From rows 34-41` subsection below is
> separately numbered and scoped to that heading — do not merge it into this list.

17. **`tree-map/03-internals-b1-key-identity-and-nulls.md` (row 44a): the exact `NullPointerException` message text printed for `new TreeMap<String,Integer>().put(null, 1)` is JDK-minor-version/flag dependent** (helpful-NPE messages vary); the exception type (`NullPointerException`, thrown from `Comparable.compareTo` on a null receiver) is guaranteed and correctly stated, only the literal message string in the shown output is not guaranteed stable. No action needed — flagged for a future accuracy pass if message text is ever quoted verbatim elsewhere.

18. **RESOLVED 2026-08-28 — Open questions item 18: the two real bugs found in the MyTreeMap
    build-it series were fixed in the shipped files, not just in a compile harness.** The
    original entry here (written earlier on 2026-08-28) claimed three bugs, one of which —
    "`04c2` calls a no-arg `getFirstEntry()`" — turned out to be false: re-reading `04c2` on disk
    shows the shipped code already calls the correct one-arg `getFirstEntry(root)`; that claim
    came from a transcription slip in the compile harness itself, not from the shipped file, and
    is retracted. The two real bugs, now fixed directly in the note files: (a) `Entry<K,V>` in
    `tree-map/04-build-my-tree-map.md` did not implement `java.util.Map.Entry<K,V>`, so
    `tree-map/04c2-build-my-tree-map-c2-iterator.md`'s `EntryIterator`/`entryIterator()` (typed
    `Iterator<Map.Entry<K,V>>`, matching the real `java.util.TreeMap`) could not compile — fixed
    by making `Entry<K,V>` `implements Map.Entry<K,V>` with `getKey()`/`getValue()` added
    alongside the existing `setValue()`, in `04-build-my-tree-map.md`, matching the real JDK
    `TreeMap.Entry` exactly (see `02b-internals-a2-entry-and-rotations.md`'s source excerpt); (b)
    no file defined `Entry.toString()`, so `04d-build-my-tree-map-d-diff-and-demo.md`'s demo
    comments claiming `40=v40`-style output were not actually true — fixed by adding
    `toString()` returning `key + "=" + value` in the same `Entry` declaration. A fresh
    extraction straight from the six shipped files — no harness patches, only the necessary
    assembly scaffolding (imports, an outer wrapper class, and skipping the two files' own
    section-level worked-example `main`/demo snippets, which is a format choice already in the
    files, not a fix) — compiles clean under JDK 21.0.7 `-Xlint:all` with zero warnings, and its
    real output is byte-identical to every comment in `04d`'s six blocks. New demo output md5:
    `713593a58eba9b6397f50ec9ec527f82`, superseding the earlier harness-only
    `81c80d60c7e78f0b4a32d2af09fe90e2`, recorded in the row-45 fold entry below.
    **Re-verified 2026-08-28, same day, with a fuller harness:** that extraction had quietly
    skipped `04c`'s own floor/ceiling/lower/higher demo block and all three of `04c2`'s
    iterator/`ConcurrentModificationException`/`IllegalStateException` demo blocks, running only
    `04d`'s demo. A second run assembled every class-member block from `04`/`04b`/`04b2`/`04c`/
    `04c2` in file order (fixAfterDeletion's cases A/B from `04b` spliced with `04b2`'s C/D and
    mirror-branch continuation, per this series' documented multi-file method split) plus *every*
    demo/bare-statement snippet from `04c`, `04c2`, and `04d` (excluding only `04c`'s
    wrong-on-purpose `floorEntryWrong` block and each file's own section-level `main`) into one
    `Demo.main`. It still compiles clean under JDK 21.0.7 `-Xlint:all`, zero warnings, zero
    errors — **no bugs remain in the shipped files** — and every `//` comment across all three
    files' demos matches the real printed output exactly, with no mismatches. This confirms item
    18's two fixes are complete and sufficient; the earlier "three bugs" claim's retraction above
    still stands. New, fuller demo output md5, from the published files as they now stand:
    `2e25f2a9af71f7e984001d8b8e306b26`, superseding `713593a58eba9b6397f50ec9ec527f82` as the
    canonical proof for this row.
    **Consolidated 2026-08-28:** a fourth pass, using the same fuller assembly but leaving `04c2`'s
    second `it3.remove()` uncaught exactly as the shipped source shows it, got a different,
    equally honest md5 (`d393e9a1875c77d89daaffe16b2bd5e8`) because the process then terminates
    before `04d`'s section ever prints — a harness-assembly difference, not a false claim by
    either run. `2e25f2a9af71f7e984001d8b8e306b26` has since been independently reproduced twice
    more from the shipped files (unchanged in code content since this fix, only prose/header
    edits) and is the canonical value; the exact harness that reproduces it, and the commands
    used, are pinned in the row-45 fold entry below, which is corrected to match.

12. **RESOLVED 2026-08-27 — row 28 split in two; the coverage hole is closed.**
    `linked-list/02-build-my-linked-list.md` (600) covers leaves 4.2.1–4.2.4 and
    `linked-list/03-build-my-linked-list-b-iterators-and-benchmark.md` (497) covers 4.2.5–4.2.8
    (`ListItr`, `descendingIterator`, the diff, the mid-insert benchmark). Both under the 600
    ceiling, both footers verified against `wc -l`. **All 901 leaves are now owned by exactly
    one file — there is no coverage gap anywhere in the set.** Benchmark numbers in row 28b were
    re-measured in a private scratch dir after the shared one was found contended; see item 14.

16. **Two `ArrayDeque` version claims corrected, and one of them is a SECOND trap nobody states
    (rows 29, 30, 30b).** Verified by reading `ArrayDeque.java` across five JDKs rather than
    recalled. (a) The power-of-two mask and the power-of-two capacity requirement are **JDK 8
    only**; JDK 9 already has `inc`/`dec`/`sub` and no mask (JDK 9 source, `inc` at line 217;
    JDK 8u202's masked `addFirst` at line 234, `calculateSize` at line 121). (b) The no-arg
    capacity change to 17 landed in **JDK 12**, not JDK 9 — JDK 8u202 line 192, JDK 9 line 182
    and JDK 11.0.27 line 183 all allocate `new Object[16]`; JDK 12, 13, 14, 17.0.15 and 21.0.7
    allocate `new Object[16 + 1]`. So there were **two** changes, nine releases apart, and
    before JDK 12 a default `ArrayDeque` held only 15 elements despite its javadoc promising 16.
    **Consequences for unwritten rows:** row 73's D-152 version-stale table lists "`ArrayDeque`
    power-of-two masking" as one trap — it is two, and the 16-versus-17 half is the better
    question. Rows 5 and 7b are already written and were not read by this lane; if either
    attributes the initial-capacity change to the JDK 9 rewrite, that is wrong.
39. **Fibonacci/pairing heap performance is unverified (leaf 3.5.20, row 32).**
    `priority-queue/02-internals-b-traps.md` states that array binary heaps beat Fibonacci heaps
    in practice for Dijkstra, and gives structural reasons (node size ~40 bytes vs 4, pointer
    chasing, amortised-vs-worst-case bounds, implementation intricacy) that are verifiable from
    the algorithms themselves. No published benchmark's numbers are reproduced, and none was
    re-confirmed against its source. Flagged `**Unverified:**` inline and in that file's
    `## Open questions`. *Would settle it:* the Larkin, Sen and Tarjan experimental study of
    priority queues, or a DIMACS Implementation Challenge shortest-path report with per-structure
    timings on named graphs.
40. **No JMH figures published for rows 30/30b or 33/33b/33c**, by the same policy as item 13.
    Both build-it sets are verified *functionally* against the JDK — `MyArrayDeque` reproduces
    `java.util.ArrayDeque`'s logical order across a wrap and a grow, and `MyPriorityQueue`
    reproduces `java.util.PriorityQueue`'s exact array layout and capacity ladder — but the
    remaining differences are single folded array loads and hoisted branches, which a wall-clock
    loop in a `main` cannot resolve from JIT warm-up noise. Flagged `**Unverified:**` inline.
    *Would settle it:* a JMH harness on the target machine with a named CPU, a named JDK build
    and `-prof perfnorm`.
14. **`/tmp/jc-build-linkedlist/` is CONTENDED — do not use it.** The row-28 writer found its
    scratch harness (`MyLinkedList.java`, `Demo.java`, `Bench.java`) overwritten mid-task by
    another agent's versions with different section comments, different demo numbering and a
    differently shaped benchmark. It moved to a private dir and **re-measured every number in
    row 28b from that private build**, so the published figures are self-consistent. Lesson for
    any resumed run: give each writer its own scratch path (`/tmp/jc-build-<row>-private/`), and
    never reuse a shared build dir across concurrent writers — a stale class file silently
    produces numbers that do not match the code on the page.

15. **MEASURED 2026-08-27 — writes through a reversed view, settled by running it.** Two
    related claims circulated this run, one of them retracted as unverified. Both are TRUE on
    **JDK 21.0.7 aarch64**, measured directly:
    - `list=[A,B,C]; var r=list.reversed(); r.addFirst("X")` -> `list=[A, B, C, X]`,
      `r=[X, C, B, A]`. So `addFirst` on the view is `addLast` on the source. This is what the
      D-25 caption and `sequenced-collections/01-sequenced-collections.md` already assert —
      **correct as written, no edit needed.**
    - `l2=[a,b]; var r2=l2.reversed(); r2.add("c")` -> `l2=[c, a, b]`, `r2=[b, a, c]`. A plain
      `add` through the view appends to the view and therefore lands at the **front** of the
      source. This was the claim flagged as unpublished-and-unmeasured; it holds.
    - `l3` (`LinkedList`) `=[a,b]; var r3=l3.reversed(); l3.addFirst("z")` -> `r3.size()==3`,
      `r3=[b, a, z]` — the view is live, not a snapshot.
    Nothing in the set needs changing as a result; this entry exists so the next writer does not
    re-flag it as unverified. If any file states the opposite, it is wrong.

41. **VERIFIED 2026-08-27 — `LinkedList.java` (JDK 21) citation lines, all confirmed.** Five
    line numbers were relayed as verified, then withdrawn as unchecked. Checked directly against
    `java.base/java/util/LinkedList.java` in JDK 21 `src.zip`: **all five are correct.** The
    withdrawal was right procedure and wrong on the facts, so they are recorded here as settled
    rather than left for a third pass — reusable by any writer citing this class:
    `public class LinkedList<E>` **90**; `clear()` **459**; `get(int)` **486**; `set(int)` **500**;
    `add(int,E)` **517**; `outOfBoundsMsg(int)` **560**; `node(int)` **577**;
    `descendingIterator()` **996**; `class DescendingIterator` **1003**;
    `LLSpliterator.characteristics()` **1271**; `reversed()` **1285**;
    `class ReverseOrderLinkedListView` **1292**. Earlier drafts mis-cited `clear()` as 292
    (inside `removeLast`) and `outOfBoundsMsg` as 570 (inside `checkPositionIndex`); both fixed.

42. **VERIFIED 2026-08-27 — D-75's manifest hop counts are wrong; the SVG departs deliberately.**
    The manifest asks for `get(8)` at "2 hops" and a worst case of "5 hops at index 5". Derived
    from the real `node(int)` at `LinkedList.java` **577** — forward from `first` when
    `index < (size >> 1)`, else backward from `last` — `get(8)` on a 10-node chain is **1 hop**
    (backward branch, one step from `last`), and the worst case is **4 hops**, at index 4 or 5,
    i.e. `floor((size-1)/2)`. The SVG and the prose both use the correct arithmetic; the manifest
    is the thing that is wrong. `linked-list/02` carried the same `n/2` error in three places and
    was corrected. **Do not "fix" the diagram back to the manifest.**

43. **VERIFIED 2026-08-27 — `UNTREEIFY_THRESHOLD` is NOT consulted on removal. Major folklore
    correction; make sure it lands in rows 37 and 92.** The near-universal claim that a tree bin
    "reverts to a linked list once it drops below 6 entries" is false for a plain `remove()`.
    Checked in JDK 21 `HashMap.java`: there are exactly three `untreeify` call sites — **2212**
    inside `removeTreeNode`, and **2326** / **2335** inside `split()`. `UNTREEIFY_THRESHOLD = 6`
    (declared **267**) is read at **only** 2325 and 2334 — i.e. **only during a resize split**,
    never on removal. The removal path's guard (**2207–2211**) is purely *structural*:
    `root == null || (movable && (root.right == null || (rl = root.left) == null || rl.left == null))`
    — it untreeifies on tree *shape*, not on a count. Consequence: a bin can sit at 6, 5 or 4
    nodes and still be a `TreeNode` tree. The writer measured a 13-node bin staying a tree down
    to 4 and flipping at 3 on JDK 21.0.7. **The same structure holds in JDK 8** (structural site
    2053; threshold only at 2166/2175), so this is not a version change — the folklore was always
    wrong. Caveat the writer correctly flagged as unverified: the exact flip count is
    removal-order dependent, since the guard reads tree shape. Do not publish "flips at 3" as a
    universal constant; publish the mechanism and the measured transcript.

19. **VERIFIED 2026-08-27 — `TreeNode.split` is byte-for-byte identical in JDK 8 and JDK 21.**
    Extracted both 46-line method bodies and `diff`ed them: no differences. Stronger than the
    syllabus's "unchanged in shape" — it is literally the same source. Useful when answering
    "what changed in `HashMap` since 8": the treeify/split machinery did not.

20. **VERIFIED 2026-08-27 — leaf 3.6.42 is too loose: a treeified bin does NOT iterate in
    insertion order.** The syllabus's "table order, then bin order" implies bin order is
    insertion order. True for a linked bin, false once the bin treeifies. `HashMap` keeps the
    `next`/`prev` chain alive alongside the tree, and **`moveRootToFront`
    (`HashMap.java:1990`)** splices the current red-black root to the head of that chain —
    `tab[index] = root; root.next = first; root.prev = null` — unlinking it from wherever it
    sat. It is called from `treeify` (**2110**), `putTreeVal` (**2173**) and the removal/split
    path (**2284**), so **the head of a treeified bin is whichever node is currently the tree
    root, and a rebalance changes it.** `putTreeVal` also splices a new node next to its tree
    parent rather than appending. Corrected rule stated inline in
    `hash-map/05a1-internals-e1b-iteration-order.md`, with the measured transcript from
    `04-internals-d-treeify.md`. Interview-relevant: "iteration order is table order then
    insertion order within a bin" is the expected answer and is wrong for treeified bins.

21. **VERIFIED 2026-08-27 — `Hashtable`'s "prime capacity" is folklore, with the arithmetic.**
    `Hashtable.rehash` grows by `newCapacity = (oldCapacity << 1) + 1` — **identical in JDK 8
    (`Hashtable.java:395`) and JDK 21 (`:412`)**, so the version half of the claim is confirmed
    by diff, not assumed. From the default 11 the capacity sequence is 11, 23, 47, 95, 191, 383,
    767, 1535, 3071, 6143, 12287, 24575, 49151, 98303, 196607. **Exactly 6 of those 15 are
    prime** (11, 23, 47, 191, 383, 6143); the rest factor cleanly — 95 = 5x19, 767 = 13x59,
    1535 = 5x307, 3071 = 37x83, 12287 = 11x1117, 24575 = 5x4915, 49151 = 23x2137,
    98303 = 197x499, 196607 = 421x467. **Correction to the writer's summary:** the last prime is
    at step **10** (6143), not step 9 — none after step 10. So "`Hashtable` uses prime capacities
    for better distribution" is false past the first few growths; `2n+1` is not prime-preserving
    and the class never tests for primality. The 12287 = 11x1117 case is the good aliasing
    example: keys congruent mod 11 collide in a way a power-of-two mask would not reproduce.

22. **VERIFIED 2026-08-28 — treeification does NOT bound collision DoS unless the keys are
    `Comparable`. This invalidates any unqualified "treeify makes it O(n log n)" claim, including
    in rows 70-73.** `TreeNode.find` compares with `compareComparables`; when the comparison is
    undecidable it searches the left subtree and then **recurses into the right as well**
    (`pr.find(h, k, kc)`), because `putTreeVal` ordered the node by `tieBreakOrder` — class name,
    then `System.identityHashCode` — which is not a real total order over the keys. So a
    non-`Comparable` colliding key degrades to searching both subtrees. Measured on JDK 21.0.7 /
    M4 Pro with 20,000 identical-hash keys: plain chain **312 ms**, treeified `Comparable`
    **2.06 ms**, treeified **non-`Comparable` 529 ms** — i.e. *worse than no tree at all*. The
    JDK class comment concedes the point. `String` is `Comparable`, so the real-world attack
    surface (CVE-2011-4858) is genuinely covered; a custom key type gets no protection. **Every
    statement of the treeify defence must carry the `Comparable` qualifier.**

23. **VERIFIED 2026-08-28 — `LinkedHashMap.linkNodeLast` was renamed `linkNodeAtEnd` in JDK 21.**
    JDK 21 `LinkedHashMap.java:236` declares `linkNodeAtEnd`, opening with a
    `if (putMode == PUT_FIRST)` branch added when `putFirst`/`putLast` arrived with `SequencedMap`
    (`PUT_FIRST` declared :331). JDK 8 has `linkNodeLast` at **:222**. The syllabus uses the old
    name at leaf 3.7.3. Cite the version-appropriate name; belongs in row 73's version-stale table.

24. **VERIFIED 2026-08-28 — the JDK's own Poisson table has a wrong last digit.** The
    `HashMap` class comment at **`HashMap.java:195`** gives k=4 as `0.00157952`. The true value
    is `e^-0.5 * 0.5^4 / 4!` = `0.00157950693...`, which rounds to **`0.00157951`**. The other
    nine rows are exact. Quote the JDK's figure when quoting the comment verbatim, but do not
    reproduce it as the mathematical value — and it is a good "I read the source closely" detail.

25. **VERIFIED 2026-08-28 — `LinkedHashMap.afterNodeAccess` contains dead code, unreachable
    since JDK 8.** The `else last = b;` arm cannot execute. Proof from the guard: the method only
    enters that block when `(last = tail) != e`, so `e` is not the tail, so `e` necessarily has a
    successor, so `a = p.after` is never null and the `if (a != null)` branch always wins.
    JDK 21's guard is `(putMode == PUT_LAST || (putMode == PUT_NORM && accessOrder)) &&
    (last = tail) != e`; JDK 8/17's is `accessOrder && (last = tail) != e` — **both have the
    property**, so this is long-standing defensive dead code, not a JDK 21 regression. State it
    as proven-unreachable with the reduction, not as "appears unreachable".

26. **VERIFIED 2026-08-28 — leaf 3.7.8's access-relink list is incomplete.** It names only
    `get`/`getOrDefault`/`containsKey`. `afterNodeAccess` actually has **eight** call sites in
    JDK 21 `HashMap.java` — 663, 1166, 1178, 1223, 1234, 1273, 1329, 1400 — so `putIfAbsent`
    (via `putVal`, 663) and `computeIfAbsent` (1223) **on an already-present key also relink**
    in access-order mode, while `Entry.setValue` does not relink and does not bump `modCount`.
    Also confirmed: `LinkedHashMap` overrides `forEach` (`LinkedHashMap.java:981`) and
    `replaceAll` (:991), walking `head`/`after`, so access-order conclusions about those hold
    through LHM's own override rather than `HashMap`'s.

27. **POLICY CHANGE 2026-08-28 — the 600-line ceiling is now a TARGET, with a hard cap of 800
    for INTERNALS and build-it files.** Decided by the run owner after the ceiling failed
    repeatedly and the splitting churn started causing worse defects than the overruns did.
    Evidence: §3.6's 5 planned rows became 14 files and §4.3's one became 8; six writers returned
    `blocked` at 719-935; five files sit at 614-753 after splitting; and the churn produced
    mis-named split children, index rows left `planned` while their files existed, and a row-45
    proof that took three attempts. The overruns are structurally mandated, not padding: a
    `[SOURCE]` line must be quoted *and* explained, a `[PROVE]` claim needs a compiled program
    plus its real output, and the required ending (pitfalls + cheat sheet + self-test) is a fixed
    150-215 lines that a smaller body cannot amortise. **Rules now:** aim for 600; publish up to
    800 when the excess is provably source quotes, runnable programs or the required ending, and
    say so in the report; above 800, split. **Never compress mechanism, and never split so far
    that one method or one class is scattered across files.** Files currently over 600 and
    ACCEPTED under this policy: `linked-hash-map/01a` (753), `01c` (729), `01b` (644),
    `tree-map/03b` (636), `tree-map/04` (614).

28. **VERIFIED 2026-08-28 — a behaviour-preserving md5 is a property of the notes PLUS the
    harness, and is unfalsifiable if recorded bare.** Established the hard way on row 45: two
    honest runs over the same shipped files produced different md5s (`2e25f2a9…` vs `d393e9a1…`)
    purely because one wrapped 04c2's deliberately-throwing `it3.remove()` in try/catch and the
    other ran it verbatim, letting the uncaught `IllegalStateException` truncate stdout before
    04d printed. A real number was consequently written into the index as "never actually run".
    **Every build-it proof must pin the harness beside the number:** which blocks were included,
    which excluded and why, which were spliced into a single method rather than added as members,
    any behavioural wrapping of a throwing snippet, and the exact `javac` / `java` / `md5`
    command lines. Blocks in a build-it series are **not** naively concatenable — they split into
    class members, bare statements belonging in `main`, and deliberate counter-examples (e.g.
    `04c`'s `floorEntryWrong`, marked WRONG, which must be excluded or the compile fails for a
    non-defect). Per-file snippet scopes need their own braces, since files reuse local names.

29. **RESOLVED for `tree-map/` and `sets/` on 2026-08-28 — a pedagogical "this throws" snippet
    upstream of later demos breaks the reader's own run.** Falls out of item 28. In `tree-map/`, a
    reader typing out 04c2 then 04d got an uncaught `IllegalStateException` from `it3.remove()`
    and never saw 04d's output. **Fixed:** `04c2-build-my-tree-map-c2-iterator.md`'s
    `it3.remove()` demo now wraps the second call in `try { it3.remove(); } catch
    (IllegalStateException ise) { System.out.println("caught: " + ise); }`, mirroring the
    `ConcurrentModificationException` demo already in that same file — the reader still sees that
    it throws and what it throws, but a verbatim transcription now runs to completion with no
    harness wrapping needed at all (re-proved in row 45's history above, same md5
    `2e25f2a9af71f7e984001d8b8e306b26`). **Swept the rest of `tree-map/` and `sets/`** for the same
    shape: every other `throw new`/`catch` occurrence in both directories was inspected —
    `tree-map/02b`'s `AssertionError`s, `tree-map/03`'s `NullPointerException`/`ClassCastException`,
    `tree-map/03b`/`03b2`'s `IllegalArgumentException`, and `sets/01b`'s
    `IllegalArgumentException` — all are either method-definition guard clauses (never executed as
    a standalone demo statement) or single-file demos whose own `catch` already sits right next to
    the throwing call; none sit upstream of a later demo in the same series the way `04c2`'s did.
    `sets/` has no build-it series spanning multiple files the way `tree-map/04`–`04d` does, so no
    cross-file instance of this shape exists there. No open instance remains in either directory;
    the defect may still exist elsewhere in the pipeline (other topics' build-it series), which is
    outside this sweep's scope.

30. **VERIFIED 2026-08-28 — D-103 is defective; the SVG needs re-cutting.** Its annotation on
    `reversed().reversed()` claims "a view of a view, two objects deep, not the original map
    returned by identity". The opposite is true. `ReversedLinkedHashMapView.reversed()` is
    `return base;` at **`LinkedHashMap.java:1224`**, so double reversal hands back the original
    object. Measured on JDK 21: `m.reversed().reversed() == m` prints **`true`** and
    `r.reversed().getClass()` is `java.util.LinkedHashMap`, not a view class. Corrected in prose
    at the embed point in `linked-hash-map/01c`; **the SVG still carries the wrong annotation.**
    Third manifest/diagram defect in this set after D-115 and D-75 — the manifest is a suspect,
    not an authority.

31. **MANDATORY EXCLUSION LIST for rows 70-73 — exactly two files, by name.** An aggregate pass
    that globs `**/*.md` will pick these up; both have a full H1, plausible prose and no row in
    the file plan. Both are retained deliberately (the user ruled against deletion, and `rm` is
    denied at settings level), both carry a `> **SUPERSEDED - DO NOT READ, DO NOT CITE.**` banner
    directly under the H1, and both footers read `Leaves covered: none - SUPERSEDED`:
    - `array-list/06-build-my-array-list-b-views-and-bulk.md` (1069 lines) - superseded by rows
      26c/26d/26e.
    - `tree-map/03b-internals-b2-buildfromsorted-and-views.md` (636 lines) - superseded by rows
      44b1/44b2.
    **Verification for whoever writes 70-73:** the correct file set is exactly the paths carrying
    a `done` row in the file plan above. Do not glob the tree. Cross-check: 105 `done` rows and
    107 `.md` files excluding the two `00-*` files - the difference is these two, and nothing
    else. If that arithmetic stops holding, something new is unrecorded and must be resolved
    before the aggregate files are written.

32. **RESOLVED 2026-08-28 - item 29 swept clean across `tree-map/` and `sets/`; the fix is
    verified by md5 identity.** `tree-map/04c2`'s `it3.remove()` now ships inside try/catch
    printing `caught: java.lang.IllegalStateException`, mirroring the CME demo above it.
    Re-proved from the shipped files: `javac -Xlint:all` exit 0, zero warnings, stdout md5
    **`2e25f2a9af71f7e984001d8b8e306b26`** - **byte-identical to the earlier harness-wrapped
    run.** That identity is itself the proof the fix only relocated the try/catch from harness
    into the note, so a reader transcribing verbatim now gets exactly what the harness got. The
    remaining `throw`/`catch` instances in both folders (`02b` AssertionErrors, `03` NPE/CCE,
    `03b`/`03b2` IAE, `sets/01b` IAE) are guard clauses inside method bodies that never run as
    standalone demo statements, or single-file demos whose catch already sits beside the throw.
    `sets/` has no multi-file build-it series, so no cross-file instance can exist there.
    **Lesson: apply item 29 at first write, not as a sweep** - the peer confirmed the retrofit
    cost far more than doing it up front on row 69.

33. **2026-08-28 - the ordering invariant is now backed by INSTRUCTION ONLY. Treat it as
    load-bearing.** A blanket `"Bash"` allow was added to `.claude/settings.local.json` (with the
    user's approval) to stop approval prompts. The deny list still wins and still covers `rm`,
    `sudo`, `git push`, `git commit`, `git reset`, `git checkout` - so a delete still fails
    loudly. **But nothing on the deny list covers overwriting.** `mv`, `chmod`, `dd`, `truncate`
    and shell redirects are all permitted. This set has already lost a finished 401-line file to
    a delete-first ordering and had four finished files truncated to zero by an in-place
    line-count script. Both would now be *unblocked*. Rules, restated because they are the only
    remaining protection:
    - **Never write to a path you did not create this run** without reading it first and
      confirming it is not a finished file. A heredoc redirect over an existing path is a silent
      total overwrite and is exactly what `rm` denial does not prevent.
    - **Write new, verify on disk, update the index, only then retire the old.** Never let a
      `done` row point at a path that does not exist.
    - **Writers write-then-rename**, never open-for-write in place.
    - **One writer per output path, ever.** If a writer reports its file changed underneath it,
      that is real evidence of another agent - report it, do not rationalise it.
    - Per-row private scratch dirs (`/tmp/jc-row<N>-private/`). Never a shared build dir: a
      contended one already produced published numbers that did not match the code on the page.

34. **VERIFIED 2026-08-28 - why the `EnumMap` reused-`Entry` folklore survives casual
    experiment.** This closes item 3 with the missing piece. `EnumMap.EntryIterator.next()` does
    allocate a fresh `Entry` per call (`EnumMap.java:567`, confirmed again), but the entries it
    returns hold only an `int index` and read `vals[index]` **live**, so a retained entry tracks
    the map (`MON=gym` -> `MON=swim` -> `MON=null`). Meanwhile `new ArrayList<>(entrySet())` gives
    **snapshots, not live views**: `fillEntryArray` (`EnumMap.java:508`) builds
    `AbstractMap.SimpleEntry` copies. So the obvious experiment - collect the entry set into a
    list and inspect it - cannot reveal either behaviour, which is exactly why the wrong model
    persists. Publish both halves: fresh allocation per `next()`, and live `vals[index]` reads.

35. **VERIFIED 2026-08-28 - three more wrong syllabus leaves in §3.10.**
    - **3.10.12 is wrong about `~elements & mask`.** `RegularEnumSet` has **no `mask` field**. The
      real form is recomputed inline: `complement()` does
      `elements &= -1L >>> -universe.length;` at `RegularEnumSet.java:61`, carrying the JDK's own
      comment `// Mask unused bits`. The negative shift distance is the trick worth explaining
      (`>>>` uses only the low 6 bits of the count, so `-n` means `64-n`).
    - **3.10.14 is wrong that `Enum` does not override `hashCode()`.** It declares
      `public final int hashCode()` at **`Enum.java:182`**. The `final` is the load-bearing part:
      you cannot give an enum a value-based hash, which is why enum-keyed hashing is identity
      based and stable within a run.
    - **3.10.14's "irreproducible per run" does not reproduce** on default HotSpot 21 - two
      separate JVMs gave byte-identical output. The writer reported the failure honestly rather
      than asserting the claim, then demonstrated the real property two other ways (one extra
      identity-hash call reorders the map; `-XX:hashCode=0` diverges across runs). Correct
      framing is **"unspecified, not random"**.
    Also: the "`remove()` reshuffle" framing does not apply to `EnumMap` at all, since
    `index == ordinal` is stable.

36. **VERIFIED 2026-08-28 with a CORRECTED repro - `IdentityHashMap.equals` really is
    asymmetric against other `Map`s, but NOT the way row 51 states it.** The finding is right;
    the recipe published with it does not reproduce, and must be fixed in
    `specialised-maps/03-identity-and-weak.md` before anyone tries it.
    - **What does NOT work** (as written): two distinct-but-equal *keys*. `ihm` then has size 2
      against `hm`'s size 1, so **both** directions return `false`. Measured. Same-identity keys
      are symmetric-`true`; equal-but-distinct keys with equal size are symmetric-`false`.
    - **What DOES work:** same key *identity*, an equal-but-distinct **value**.
      `ihm.put(k, new String("1"))` against `hm.put(k, "1")` gives
      **`ihm.equals(hm) == false` and `hm.equals(ihm) == true`.** Measured on JDK 21.
    - **Mechanism:** `IdentityHashMap.equals` (`:660`) has three branches - `o == this`,
      `o instanceof IdentityHashMap` (identity compare), and `o instanceof Map` (`:674`) which
      delegates to `entrySet().equals(m.entrySet())`. That entry set compares **values by
      identity too**, so the distinct value fails. The reverse direction runs
      `AbstractMap.equals`, which calls `ihm.get(k)` - an identity *key* lookup that succeeds -
      then compares the value with `.equals`, which succeeds. Hence the asymmetry.
    Consequence stands as written: never put an `IdentityHashMap` in a `Set` or use one as a key.

37. **VERIFIED 2026-08-28 - `IdentityHashMap(int)` takes `expectedMaxSize`, not capacity.** The
    outlier among `java.util` hash containers. `IdentityHashMap.java:234` calls
    `init(capacity(expectedMaxSize))`. Measured by reflection: `new IdentityHashMap<>(100)`
    allocates a **512-slot table** (256 capacity x 2, since keys and values interleave in one
    array), leaving room for ~170 mappings before the first resize. The javadoc explicitly
    declines to specify the relationship (`:79-80`), so callers must not hard-code the
    3x-then-round rule.

38. **VALIDATED 2026-08-28 - item 28's pinned-harness discipline works: an independent party
    reproduced a build's block classification exactly, without having built it.** Row 39's
    (`MyHashMap`) harness was re-derived from the published pages alone, applying only the two
    stated rules - a fence must be tagged `java`, and its first line must full-match
    `// (\w+\.java)`. Result: **24 included blocks**, per label
    `MyHashMap.java` 17, `MyHashSet.java` 1, `MyLinkedHashMap.java` 1, `LruCache.java` 1,
    `Demo.java` 3, `Bench.java` 1 - **identical to the writer's report.** Exclusions reconcile
    exactly too: **41** `java` blocks lacking the label, plus **36** untagged fences (the JDK
    source quotes, excluded because they carry no language tag). The writer had honestly flagged
    that its 41 was counted *before* a later no-op comment reword; this count ran after, and is
    still 41, so that gap is closed. **Two rules are what made this reproducible:** JDK quotes
    sit in bare fences so they can never reach the extractor, and inclusion is a mechanical
    full-match rather than a judgement call. Use both shapes for every remaining build-it row.
    Note also that block *order* is load-bearing - `MyHashMap.java` blocks 2-17 are class-body
    continuations and `Demo.java` block 2 is a bare continuation of `main` - so a pinned harness
    must state the order, not just the set.

13. **`array-list/08` JMH figures are unpublished by design.** The row-26 writer verified the
    harness and the `org.openjdk.jmh:jmh-core:1.37` coordinates against Maven Central but
    deliberately published no throughput numbers, flagged `**Unverified:**` inline. A
    meaningful figure needs a named CPU, a named JDK build and `-prof perfnorm` output. Either
    run it on the target machine and fill them in, or leave the harness as the deliverable.
    Do not let an agent invent plausible-looking timings.

11. **RESOLVED at the 2026-08-26 pause, with two items left for a human.** Row 26 (§4.1) is
    complete as a 4-way split; all 16 leaves verified present across rows 26/26b/26c/26d, and
    every one of the 901 leaves in the set is owned by exactly one file. Remaining:
    (a) **RESOLVED 2026-08-28 — retained, not deleted.** `array-list/06-build-my-array-list-b-views-and-bulk.md`
    (1067 lines) is the superseded first attempt; its every leaf is now covered by rows 26c and
    26d. It has no row in the file plan. The user ruled against deletion; instead it carries a SUPERSEDED banner under its H1 and a neutralised footer. Agents here remain barred from deleting files — after a
    deletion destroyed a finished 401-line file earlier in this run — and `rm` is now denied at the settings level. No human action outstanding.
    (b) **Ceiling policy: RESOLVED — five files, and verify by recompiling.** A build-it row
    does fit the 600-line ceiling if split far enough; §4.1 needed five files (600/423/545/422/
    520) where four left one at 737. The precedent to follow for rows 30, 33, 39, 41 and 45,
    all of which carry complete implementations against 400–560 estimates: split to fit, then
    **prove the split is behaviour-preserving** by extracting every `java` block in file order,
    concatenating, compiling with `-Xlint:all`, running the demo and comparing output md5
    against the pre-split build. That check is what caught nothing here — and is exactly why
    it is worth keeping.

0. **`framework/07-legacy-a-vector-stack-hashtable.md` is a reconstruction, not the original.**
   The original 401-line file was deleted from disk on 2026-08-26 by an agent belonging to a
   different session working this same plan. The file now at that path is a 489-line rewrite
   covering the same leaves (2.15.1–2.15.9), verified for header form, leaf coverage and
   diagram references, but it is not line-for-line what row 7a was first accepted at. Worth a
   read-through against its neighbours for duplicated or missing cross-references.

1. **`framework/06-matrices-and-choosing.md` (leaf 1.10.3)** — Doug Lea's exact original wording
   on why `ConcurrentHashMap` bans null could not be confirmed. The proof on the page is built
   from the current JDK javadoc's stated rationale, not from a verbatim quote of the original
   `concurrency-interest` note. *Would settle it:* the archived Lea post, or the
   `ConcurrentHashMap` class-comment history in the OpenJDK repository.
2. **`framework/08-abstract-skeletons.md` (leaf 3.18.12)** — the current Maven coordinates,
   package path and version for `guava-testlib` were not re-confirmed against Maven Central.
   The class names used (`CollectionTestSuiteBuilder`, `ListTestSuiteBuilder`,
   `MapTestSuiteBuilder`, the `Feature` enum family) are long-stable public API.
   *Would settle it:* the Maven Central listing for `com.google.guava:guava-testlib`.
3. **RESOLVED 2026-08-26 — leaf 2.2.15 is wrong; the syllabus claim must not be reproduced.**
   The leaf asserts `EnumMap`'s `EntryIterator` hands out a single *reused* `Entry` object. It does
   not. `EntryIterator.next()` does `lastReturnedEntry = new Entry(index++); return lastReturnedEntry;`
   — a fresh `Entry` per call. Verified directly against `java.base/java/util/EnumMap.java` in
   **JDK 21 (line 567)**, JDK 17 (564), JDK 25 (568) and JDK 8 (572): identical in all four, so this
   is **not** a version trap — there is no JDK in the 8–25 range where the reused-instance model
   holds. `lastReturnedEntry` is a `remove()`-support field, not an allocation optimisation:
   `remove()` reads `lastReturnedEntry.index`, repairs it after the `super.remove()` call, then nulls
   the field. **Consequences for unwritten rows:** (a) **D-115's must-show contents are wrong** where
   they assume a reused instance — the illustrator for it must depart from the manifest here, and
   should say so; (b) row 50 (`specialised-maps/02-internals-enum-map-set.md`) must state the
   fresh-allocation mechanism and correct the folklore explicitly, per the prompt's version-stale
   mandate; (c) **done** — the `**Unverified:**` note in `iteration/02-fail-fast-fail-safe.md` has been
   replaced by a "version-stale folklore, corrected" block carrying the four-JDK citation, and that
   section's closing blockquote now states the fresh-allocation fact so the correction survives a
   cheat-sheet-only re-read.
4. **RESOLVED 2026-08-26 — leaf 1.9.9, the reversed-view class names are confirmed correct.**
   The syllabus name is right: `LinkedHashMap.ReversedLinkedHashMapView` is a real static nested
   class extending `AbstractMap<K,V>` and implementing `SequencedMap<K,V>`, holding one final
   reference to the backing map — which is why writes propagate both ways through it and through its
   own `keySet`/`values`/`entrySet` sub-views. `java.util.ReverseOrderListView` is likewise the real
   `List` counterpart. Verified against the OpenJDK `LinkedHashMap` source and the JDK 21
   `SequencedMap`/`LinkedHashMap` javadoc. The file now states both names as fact and keeps the
   warning that neither is specified API, so `instanceof` checks against them are still unsafe.
5. **`sequenced-collections/01-sequenced-collections.md` (leaf 1.9.14)** — no specific named
   open-source project was confirmed to have hit the `getFirst`/`getLast` source-compatibility
   collision, so the breakage is described generically from JEP 431's own compatibility-risk notes
   rather than attributed. *Would settle it:* a JDK 21 compatibility-issue tracker entry or the
   project's own migration commit.
6. **`sequenced-collections/01-sequenced-collections.md` (leaf 1.9.13)** — whether
   `ConcurrentSkipListMap`/`ConcurrentSkipListSet` were *deliberately* excluded from the retrofit or
   simply out of initial JEP 431 scope. *Would settle it:* the JEP 431 discussion thread on
   `core-libs-dev`.
7. **`sequenced-collections/01-sequenced-collections.md` (leaf 1.9.16)** — "nothing was added to the
   collections API in Java 22–25" rests on tracking the public JEP lists, not on a javadoc diff
   across those releases. *Would settle it:* a `java.util` javadoc diff for 21 → 25.
8. **`cost-and-memory/02-internals-memory-headers.md` (leaf 3.15.1)** — the exact bit layout of the
   mark word across HotSpot lock-mode revisions is flagged inline as implementation detail. The
   8-byte total is solid; only the internal bit assignment is unconfirmed. *Would settle it:* the
   HotSpot `markWord.hpp` source for the target JDK.
9. **`cost-and-memory/03-internals-memory-collections.md` (leaf 3.15.24)** — the JDK version at which
   Valhalla value classes leave preview is not fixed; JEP 401 was reported as targeting a JDK 28
   preview as of August 2026. Flagged inline. *Would settle it:* the JEP 401 status page.
10a. **RESOLVED 2026-08-26 — leaf 3.1.32 is version-stale; the syllabus claim must not be reproduced.**
    The leaf asserts `CopyOnWriteArrayList` holds a `ReentrantLock lock`. In JDK 21 it holds
    `final transient Object lock = new Object()` — a plain monitor
    (`java.base/java/util/concurrent/CopyOnWriteArrayList.java`, JDK 21, line 107). `ReentrantLock`
    was the JDK 8 form (8u202, line 97); JDK 11.0.27 already carries the `Object` monitor (line 102),
    so the change landed between 8 and 11. Corrected inline as a version trap in
    `array-list/03-internals-c-views-and-iterators.md`. **Consequence for unwritten rows:** row 60
    (`concurrent-collections/04-copy-on-write.md`) covers leaf 3.14.24, whose "the `volatile
    Object[]` write path" framing is fine, but any writer restating the lock type must use the
    monitor, not `ReentrantLock`.
10b. **RESOLVED 2026-08-26 — leaf 3.1.31's "2x growth" is a simplification, not the rule.**
    `Vector.grow` (JDK 21, `java.base/java/util/Vector.java`, lines 256–262) passes
    `capacityIncrement > 0 ? capacityIncrement : oldCapacity` as the *preferred* growth to
    `ArraysSupport.newLength`. Doubling therefore applies only when `capacityIncrement` is zero or
    unset. Stated precisely in `array-list/03-internals-c-views-and-iterators.md`. Relevant to row 7a,
    which is already written — worth a check that it does not assert a flat 2x.
10c. **RESOLVED 2026-08-26 — D-71's caption formula is wrong for the JDK's actual growth factor.**
    `Φ = 2·size − capacity` is the classic *doubling* potential function and provably fails at
    g = 1.5, where it yields `0.5c + 3` rather than a constant. `array-list/04-amortised-analysis.md`
    embeds D-71 as the doubling case, then derives the general family
    `Φ_g = (g/(g−1))·size − (1/(g−1))·capacity`, giving `3·size − 2·capacity` and amortised 4 for the
    JDK's 1.5x. The accounting method is corrected the same way: 3 credits at g = 2, **4 at g = 1.5**.
    The manifest's must-show text for D-71 is therefore correct only for the doubling case; the SVG
    was not re-authored, the prose carries the correction.
10e. **RESOLVED 2026-08-27 — D-75's manifest hop counts are arithmetically wrong; the SVG departs
    from the manifest deliberately.** The manifest row for D-75 asks for "`get(8)` walking backward
    **2 hops** from `last`" and a "worst case at index 5 labelled with **5 hops**". Both are wrong
    against the real loop. `node(int index)`'s backward branch is
    `for (int i = size - 1; i > index; i--) x = x.prev;`
    (`java.base/java/util/LinkedList.java`, JDK 21, line 577), so on a 10-node chain (`last` is
    index 9) `get(8)` is **1 hop**, and the worst case is **4 hops** — at index 4 via the forward
    branch or index 5 via the backward branch, i.e. `⌊(size−1)/2⌋`, not `size/2`. The SVG was
    authored to the manifest, then corrected to the real arithmetic, because
    `linked-list/01-internals.md` derives the hop counts from the loop bound in prose and a diagram
    contradicting the prose is worse than a manifest departure. `linked-list/02-build-my-linked-list.md`
    carried the same `⌊n/2⌋` error in three places (prose, boxed definition, cheat sheet) and was
    corrected to `⌊(n−1)/2⌋`.
10d. **`array-list/04-amortised-analysis.md` (leaf 3.2.6)** — the golden-ratio block-coalescing
    derivation is widely credited to Andrew Koenig on `comp.lang.c++.moderated`; the thread and the
    argument were verified but the per-message byline was not. *Would settle it:* the original 2003
    posting with author headers. The folly `FBVector` half of the claim **is** verified and quoted.
    The file also flags, beyond what the syllabus asked, that the block-coalescing argument assumes a
    first-fit `malloc` — HotSpot bump-allocates in TLABs with a moving collector, so the argument is
    strong for C++ and weak for Java. That caveat is stated rather than presented as the JDK's reason.
10. **`cost-and-memory/04-observability.md` (leaves 3.17.3, 3.17.15)** — Eclipse MAT's query *UI
    labels* may differ cosmetically across MAT 1.12/1.14 (the OQL identifiers themselves were
    confirmed stable), and Error Prone's `CollectionIncompatibleType` availability depends on
    version and configuration. Both flagged inline. *Would settle it:* the MAT release notes for the
    version in use, and the Error Prone bug-pattern list for the configured version.

### From rows 34–41 (`hash-map/`, `linked-hash-map/`), appended 2026-08-28

> **Renumbered 2026-08-28 to 91–105.** These items originally restarted at 1 and collided with the main list's 30–44, which made a bare "item 43" ambiguous — the main list's 43 is the `UNTREEIFY_THRESHOLD` finding, this block's was a Caffeine note. Main-list numbers were left untouched so existing prose citations remain valid.

91. **RESOLVED — treeification does NOT bound collision DoS unless the keys are `Comparable`, and a
    non-`Comparable` tree bin is WORSE than no tree.** Measured on Apple M4 Pro, JDK 21.0.7+8-LTS-245,
    arm64, median of three runs, inserting *n* keys with identical `hashCode()`: at 20,000 keys a
    never-treeifying chain (`Hashtable`) takes 312 ms, a treeified bin of `Comparable` keys 2.06 ms,
    and a treeified bin of non-`Comparable` keys **529 ms**. Mechanism: `putTreeVal` can only use
    `compareTo` when `comparableClassFor(key)` returns non-null (the class must literally declare
    `implements Comparable<ThatClass>`); otherwise it falls back to `tieBreakOrder`, which orders by
    class name then `System.identityHashCode` — an order the *lookup* key does not share, so
    `TreeNode.find` must search both subtrees. The JDK class comment concedes it ("so long as they
    are also Comparable"). Independently reproduced by two files
    (`04c-internals-d3-collision-dos.md` and `10b-build-my-hash-map-g-diff-and-collision-dos.md`).
    **Consequence for unwritten rows:** any flat "treeify bounds it at O(n log n)" claim is wrong
    without the `Comparable` qualifier — this affects row 73's trap index and rows 70–72's Q&As.
    `String` is `Comparable`, so the JDK's defence does cover the real attack surface; a custom key
    type gets none of it. Absolute millisecond figures are flagged `**Unverified:**` inline (single-shot
    wall clock, not JMH); the scaling shape is the reproducible claim.
92. **RESOLVED — `removeTreeNode` DOES untreeify; the folklore is wrong.** The widely-repeated claim
    that only a resize split converts a tree bin back to a list does not survive the source: there
    are **three** `untreeify` call sites (JDK 21 `HashMap.java` lines 2212, 2326, 2335), and the one
    at 2212 is inside `removeTreeNode`, guarded by a **structural** test at 2207 that never references
    `UNTREEIFY_THRESHOLD`. Measured on JDK 21.0.7: a 13-node tree bin stays a `TreeNode` down to 4
    nodes and untreeifies at 3. So "untreeifies at 6 on remove" is wrong twice over — wrong threshold
    and wrong trigger. Corrected inline in `03c-internals-c3-tree-split.md`, and cross-checked
    independently by `04b-internals-d2-poisson-and-hysteresis.md`, which confirmed the guard is
    structural. *Residual uncertainty:* the measured untreeify point (3) reflects one removal order;
    other orders could trip the structural test at 4 or 5. The stated bound ("stays a tree well above
    6") holds either way.
93. **RESOLVED — leaf 3.7.3 names a method that no longer exists.** `LinkedHashMap.linkNodeLast` was
    renamed **`linkNodeAtEnd`** in JDK 21 (line 236) and gained a `putMode == PUT_FIRST` branch when
    `putFirst`/`putLast` arrived with `SequencedMap`. `linkNodeLast` is correct for JDK 8
    (`java/util/LinkedHashMap.java` line 222) and JDK 17 (line 223), and those bodies are
    byte-identical to the JDK 21 `else` arm. Verified in all three source trees by two independent
    writers. Corrected inline in `linked-hash-map/01-internals.md` with a three-row version table and
    flagged as a version trap. **Consequence for unwritten rows:** row 73's version-stale table should
    carry it; almost every write-up on the internet still says `linkNodeLast`.
94. **RESOLVED — the JDK class comment's own Poisson table has a wrong digit.** The comment prints
    `4: 0.00157952`; the true value of `e^-0.5 · 0.5^4 / 4!` is `0.0015795069…`, which rounds to
    `0.00157951`. Computed on JDK 21.0.7. The other nine published rows match exactly. Noted inline in
    `04b-internals-d2-poisson-and-hysteresis.md`. Also worth carrying forward: λ = 0.5 is the
    *time-averaged* load, not the peak — a map at load factor 0.75 sits between ~0.375 just after a
    resize and 0.75 just before the next, so the table understates bin lengths at the worst moment.
95. **RESOLVED — `Hashtable`'s growth sequence is barely prime.** `(oldCapacity << 1) + 1` from 11
    gives 11, 23, 47, 95, 191, 383, 767, 1535, 3071, 6143, 12287, … Only **6 of the first 15** are
    prime — 11, 23, 47, 191, 383 and **6,143, which is the last prime in the sequence**. The
    composites: 95 = 5×19, 767 = 13×59, 1535 = 5×307, 3071 = 37×83, 12287 = 11×1117. The rule
    produces *odd* numbers, not primes. **State the cut-off as the value 6,143, not as a step
    number** — the page numbers its table from 0 and the index numbered from 1, which made the same
    fact read as two different claims. Published with real primality output in
    `05c-internals-e4-hashtable-and-prime-modulus.md`. "Prime-ish capacity" (leaf 3.6.46) is generous.
96. **RESOLVED — an over-bound `LinkedHashMap` LRU does not drain; it stays over-bound.** The common
    claim (including in this row's own brief) that a map over its bound "drains one entry per
    subsequent put" is wrong. Measured on JDK 21: each `put` adds one and evicts at most one, so the
    net size change is **zero** — filling to 10 and then behaving as if the bound were 3 leaves
    `size()` pinned at 10 across six further puts. Corrected inline in
    `01b-internals-b-lru-and-sequenced.md` with the transcript and a pitfall entry. Related: the JDK
    javadoc for `removeEldestEntry` (lines 583–589) **permits** the method to modify the map directly,
    provided it then returns `false` — the opposite of the usual "must not touch the map" advice. Both
    violation paths are demonstrated: modify-and-return-`true` drops two entries per insertion and
    settles the cache below its bound; calling `put` from the hook gives `StackOverflowError`.
97. **RESOLVED — `LinkedHashMap` does not override `firstEntry`/`lastEntry`/`pollFirstEntry`/`pollLastEntry`.**
    All four are inherited from `SequencedMap`'s interface defaults (`SequencedMap.java` lines 151,
    168, 187, 212), which are written in terms of `entrySet()` and `reversed()`. Three consequences,
    all verified by running them: (a) `firstEntry()` returns a `NullableKeyValueHolder` — an
    unmodifiable snapshot — so `map.firstEntry().setValue(v)` throws `UnsupportedOperationException`
    where `map.entrySet().iterator().next().setValue(v)` writes through; (b) `lastEntry()` routes
    through `reversed()`, and `LinkedHashMap.reversed()` is an uncached `new ReversedLinkedHashMapView<>(this)`,
    so every `lastEntry()` call allocates a view plus its entry-set view plus an iterator — `firstEntry()`
    and `lastEntry()` are asymmetric in allocations; (c) only the two *write* methods, `putFirst` and
    `putLast`, got real overrides. Detailed in `01c-internals-c-sequenced-and-caching.md` with a
    ten-row surface table. *Residual uncertainty:* the allocation byte counts were measured with
    `-XX:-DoEscapeAnalysis`; the steady-state cost under the default JIT with scalar replacement was
    not measured.
98. **`putFirst` on an access-order `LinkedHashMap` inverts recency** (leaf 3.7.14). `putFirst` sets
    `putMode = PUT_FIRST`, which bypasses the `accessOrder` conjunct in `afterNodeAccess`'s guard and
    moves an existing entry to the **head** — the eviction end. So on an LRU, `putFirst(k, v)` marks
    `k` as *least* recently used: a "keep hot keys at the front" refactor is an anti-optimisation.
    Verified by running it on a capacity-3 access-order map. Also measured: `putFirst` of an *absent*
    key on a full LRU inserts at the head and immediately self-evicts, returning `null` and leaving
    the map unchanged.
99. **Row 39's build cross-references `../utilities/04-map-default-methods.md` (row 65), which is
    planned but unwritten.** The link is correct against the plan and resolves once row 65 lands.
    Flagged so that a later pass does not "fix" it by deleting the reference. The same applies to
    references to `../concurrent-collections/01-thread-safety-and-wrappers.md` and `/02-internals-chm-a.md`
    (rows 57, 58) and `../immutable-collections/01-views-copies-snapshots.md` and `/04-internals-immutable-collections.md`
    (rows 53, 56) from several files in this block.
100. **No JMH figures published anywhere in rows 34–41**, by the same policy as items 13 and 18. Every
    measurement on the page is single-shot wall clock on **Apple M4 Pro, arm64, JDK 21.0.7+8-LTS-245**,
    median of three runs where a median is quoted, flagged `**Unverified:**` inline with the words
    "the shape is the finding, not the absolute numbers". The claims that rest on *shape* — the n²
    signature of a collision chain, the ~150× `Comparable`/non-`Comparable` gap, the ~14,000× ratio for
    `containsValue` on a shrunken map, the 1.96× modulo-versus-mask cost — reproduce on every run.
    *Would settle the absolute figures:* a JMH harness on the target machine with `-prof perfnorm`.
101. **`04c-internals-d3-collision-dos.md` could not pin three secondary facts to primary sources.**
    (a) The 28C3 per-platform request-size-to-CPU-time table was found only in contemporary press
    coverage, not in the slides — the mechanism is stated without the figures. (b) Tomcat's
    `maxParameterCount` default of 10,000 and its negative-means-unlimited semantics come from the
    Tomcat 7 connector docs rather than the 7.0.23 changelog; the attribute name and its role in the
    CVE-2011-4858 fix *are* confirmed. (c) The specific OpenJDK issue that *removed* alternative
    hashing was not located; JEP 180 states the intent. One correction worth keeping: **JDK-8023463
    is not the treeification issue** — the authoritative citation is **JEP 180**, "Handle Frequent
    HashMap Collisions with Balanced Trees", issue **JDK-8046170**. *Would settle them:* the 28C3
    slide deck, the Tomcat 7.0.23 changelog, and the OpenJDK issue history for `HashMap`.
102. **JDK 8's `Hashtable.java` and `HashSet.java` are absent from `/tmp/jdk8src/`**, which holds only
    `ArrayList`, `ArrayDeque`, `HashMap` and `LinkedHashMap`. So the claim that `Hashtable`'s default
    capacity 11, `2n+1` growth and modulo index are unchanged since 1.0 could not be confirmed by
    diff and is flagged `**Unverified:**` in `05c-internals-e4-hashtable-and-prime-modulus.md`.
    *Would settle it:* unpacking the full JDK 8 `src.zip`, which is present at
    `/Library/Java/JavaVirtualMachines/jdk1.8.0_202.jdk/Contents/Home/src.zip`.
103. **`afterNodeAccess`'s `a == null -> last = b` arm appears unreachable in JDK 21.** The `&&` binds
    across the whole `||` group, so the `(last = tail) != e` test excludes the case on both the
    `accessOrder` and `PUT_LAST` paths. No input reaching it could be constructed, and no CSR or bug
    report explaining its retention was found. Recorded in
    `01a-internals-a2-hooks-and-access-order.md`'s `## Open questions`. *Would settle it:* the OpenJDK
    review thread for the JDK 21 `SequencedMap` changes to `LinkedHashMap`.
104. **Two `**Unverified:**` items carried from row 40c1.** Caffeine's "within 99% of Belady's optimal"
    hit rate is the project's own wiki claim, attributed rather than reproduced; and Caffeine 3.2.4 was
    the latest Maven Central release found as of 2026-08, sourced from a page whose version table
    rendered incompletely, so the version is perishable.
105. **`MyHashMap`'s treeified bin is a sorted array, not a red-black tree, and the tradeoff is
    measured** (leaf 4.3.7). Binary search gives the same **O(log n) lookup** as the JDK's tree — 10.20 ms
    versus 10.42 ms per 100,000 gets at 20,000 colliding keys — but insertion into a sorted array is
    **O(n)**, so filling costs 222 ms against the JDK's 1.43 ms. The build therefore bounds lookup and
    not insert, where the JDK bounds both; there is no untreeify, no `split` fast path and no
    `tieBreakOrder` fallback. Stated at the code and in the diff table. Also a deliberate addition with
    no JDK counterpart: a `SortedBin.overflow` chain for keys of a class that fails the `Comparable`
    screen arriving in an already-converted bin — the JDK handles that case inside the tree via
    `tieBreakOrder`.

### From rows 57–61 (`concurrent-collections/`), appended 2026-08-28

Numbered from 61 per the numbering rule at the head of `## Open questions` — these are in the main
sequence, not a separately-numbered subsection.

61. **VERIFIED 2026-08-28 — leaf 3.14.8's `sizeCtl` encoding reproduces a STALE JDK JAVADOC, not the
    code. The famous `-(1 + resizers)` figure has not been true since Java 8 shipped.** The field
    comment at `ConcurrentHashMap.java:792-799` does say "-1 for initialization, else `-(1 + the
    number of active resizing threads)`", and essentially every write-up on the internet repeats it.
    The code does something else entirely. The **first** resizer CASes
    `sizeCtl = (resizeStamp(n) << RESIZE_STAMP_SHIFT) + 2` — `addCount` **:2353**, `tryPresize`
    **:2413-2414** — and each **helper** CASes `sc + 1` (`addCount` **:2350**, `helpTransfer`
    **:2373**). So the low 16 bits hold `2 + helpers` and the high 16 hold a *stamp identifying which
    table size is being resized*, which is what stops a thread from joining a resize that has already
    finished and restarted. `resizeStamp(n) = Integer.numberOfLeadingZeros(n) | (1 << 15)`
    (**:2284-2286**), `RESIZE_STAMP_BITS = 16` (**:575**), `RESIZE_STAMP_SHIFT = 16` (**:586**),
    `MAX_RESIZERS = 65535` (**:581**). **Worked arithmetic, checked twice:** for `n = 16`,
    `numberOfLeadingZeros(16) = 27`, `resizeStamp(16) = 27 | 32768 = 32795`, and `32795 << 16` is
    `0x801B0000` = 2,149,253,120 unsigned, i.e. **-2,145,714,176** as a signed `int`; the first
    resizer therefore sets `sizeCtl = -2145714174`, **not `-2`**. The two states the leaf gets right
    are `-1` for initialising (the CAS at **:2296**) and positive-for-threshold. D-129 draws the real
    value in green beside the javadoc's `-2` in red, because the contrast is the teaching point.
    *An orchestrator arithmetic slip is recorded here deliberately:* the illustrator brief for D-129
    carried **-2145517568** for `32795 << 16`, which is wrong; the illustrator recomputed it,
    reported the departure, and drew the correct **-2145714176**. The published diagram is right.
    **Consequence for unwritten rows:** row 73's version-stale table should carry this, and it is a
    strong "I read the source, not the comment" interview detail — the JDK's own field comment is the
    trap.

62. **VERIFIED 2026-08-28 — leaf 3.14.29 is version-stale: `SynchronousQueue`'s
    `TransferStack`/`TransferQueue` do not exist in JDK 21.** Diffed across two source trees rather
    than recalled. **JDK 8u202** has exactly what the leaf describes: `abstract static class
    Transferer<E>` (**:168**) with two implementations, `static final class TransferStack<E>`
    (**:211**, the unfair default) and `static final class TransferQueue<E>` (**:526**, fair mode).
    **JDK 21** replaced the pair with a single `static final class Transferer<E> extends
    LinkedTransferQueue<E>` (**:152**); Lifo (unfair) mode is the added `xferLifo` method
    (**:167**), Fifo (fair) mode is inherited from `LinkedTransferQueue`, and the choice is made at
    **:235** by `return (fair) ? x.xfer(e, nanos) : x.xferLifo(e, nanos);`. The class comment
    (**:132-135**) states the new arrangement outright. So `SynchronousQueue` is now *implemented in
    terms of* `LinkedTransferQueue`, which also explains why leaf 3.14.32's dual-queue material and
    3.14.29's are the same machinery seen twice. The *behaviour* the leaf describes — zero capacity,
    direct handoff, `isEmpty()` always true — is unchanged; only the class names are wrong.
    D-135 labels the JDK 21 arrangement and calls the departure out on the diagram.
    **Consequence for unwritten rows:** row 73's version-stale table; the class names are what an
    interviewer who read a 2013 blog post will expect.

63. **VERIFIED 2026-08-28 — D-132's manifest text is wrong on the CoW lock type, confirming item
    10a from the other direction.** The manifest row for D-132 asks for "a writer taking the
    `ReentrantLock`". JDK 21 `CopyOnWriteArrayList` holds `final transient Object lock = new
    Object()` (**:107**) and its mutators use `synchronized (lock)`; JDK 8u202 held a
    `ReentrantLock` (**:97**). The SVG draws the plain monitor and carries an amber "JDK 8 used a
    `ReentrantLock` here — version trap" box. **Do not "fix" the diagram back to the manifest.**
    Fourth manifest/diagram defect in this set after D-115, D-75 and D-103.

64. **PROCESS — rows 53–56 were double-dispatched and this lane withdrew from them.** Two agents
    were given `immutable-collections/` (rows 53–61 to this lane, an overlapping range to another).
    This lane discovered the collision *before writing anything there*: the index already carried a
    detailed 53/53b/53c/53d/54/54a/54b/55/55b/56/56b/56c pre-split it had not made, row 53 was
    already `done` at 598 lines, and five files were on disk timestamped within the preceding ten
    minutes. It **withdrew from rows 53–56 rather than overwrite finished work** and took 57–61
    only, per the "one writer per output path, ever" rule and item 33's warning that nothing on the
    deny list prevents an overwrite. **One artifact crosses the boundary and must not be
    re-authored:** `diagrams/D-121-listof-vs-arraylist-memory.svg` (row 56's) was authored by this
    lane's illustrator pass before the collision was found. It is correct and verified against
    `ImmutableCollections.java:553-568` — `List12` declares exactly `e0` and `e1`, `e1` typed
    `Object`, no backing array — and row 56's writer should embed that path rather than draw it
    again. `concurrent-collections/` was empty on disk and had no sub-rows, so 57–61 are
    unambiguous.

84. **CONSOLIDATED with item 68 — same finding, reached independently. Numbered 65 on first write,
    renumbered 2026-08-28 to resolve a collision** (this lane and the run owner appended
    concurrently and both used 65–71; the earlier block at items 65–83 keeps those ids per the
    numbering rule, and this lane's later duplicates moved to 84–90). Item 68 is canonical for the
    conclusion; this entry is retained for the mechanical detail it adds. **Leaf 3.14.6 is WRONG.
    The `synchronizedMap` views DO share the outer mutex, in both JDK 8 and JDK 21.** The leaf warns that "the `synchronizedMap(...).keySet()` view
    is *not* synchronized on the same mutex in all JDK versions — check before relying on it." It
    was checked, in both trees: `Collections.SynchronizedMap.keySet()`, `values()` and `entrySet()`
    pass the **identical outer `mutex` field** into every derived view's constructor — JDK 21
    `Collections.java:2912-2934`, JDK 8u202 `:2604-2623`. No divergence between the two versions.
    So the warning is unfounded across 8-through-21 and the view **is** safe to iterate under
    `synchronized (theWrapper)`. Stated as a finding in `concurrent-collections/01-thread-safety-and-wrappers.md`,
    which also flags in its own `## Open questions` that pre-Java-5 source was not available to rule
    out an older divergence — so the leaf may be describing something true of JDK 1.2/1.4.
    **What remains true and is the useful half:** `SynchronizedCollection.iterator()` returns the
    **raw underlying iterator with no synchronization at all**, and its own comment says so — which
    is the mechanical reason leaf 3.14.4 holds, and much stronger evidence than quoting the javadoc.

85. **CONSOLIDATED with item 67 — same finding, reached independently; renumbered from 66 on
    2026-08-28 per the collision note in item 84.** Item 67 is canonical for the conclusion and
    carries the run owner's own single-threaded transcript; this entry is retained for the call-site
    enumeration and the three-case sort. **Leaf 3.14.19 is imprecise: a recursive `computeIfAbsent`
    on `ConcurrentHashMap` does NOT deadlock, it throws
    `IllegalStateException("Recursive update")`.**
    JDK 21 detects the re-entry. Nine call sites, all confirmed by grep: `putVal` **:1062-1063**,
    `computeIfAbsent` **:1742** and **:1762-1763**, `compute` **:1958** and **:1990-1991**, plus
    **:1862-1863**, **:2100-2101**, **:2551-2552**. Mechanism: `computeIfAbsent` on an *empty* bin
    installs a `ReservationNode` (**:1702**, hash `RESERVED = -3`) and holds its monitor while the
    mapping function runs; a re-entrant call that lands on a bin holding a `ReservationNode` is
    recognised and thrown rather than allowed to corrupt or hang. **Three cases, and all three must
    be stated because the folklore collapses them into one:** (a) the mapping function inserting a
    key that lands in a **different** bin **succeeds** — and is still a javadoc-contract violation
    ("must not attempt to update any other mappings of this map"), so it is a latent bug rather than
    a supported pattern; (b) the **same reserved bin** throws, **deterministically, on one thread**;
    (c) a genuine **two-thread** deadlock is constructible — two threads each holding one bin's
    monitor and each needing the other's — but is **not deterministically demonstrable**.
    `synchronized` being **reentrant** is why case (b) cannot self-block on the same monitor, which
    is exactly the bit the folklore misses. Demonstrated with real compiled output in
    `concurrent-collections/03-internals-chm-b.md`, with the throw caught and printed per item 29.
    Also worth carrying: the same mistake gives **three different failure modes** across `HashMap`
    (`ConcurrentModificationException`), `ConcurrentHashMap` (`IllegalStateException`) and a
    synchronized wrapper — a good comparison table and a good interview question.

86. **VERIFIED 2026-08-28 (renumbered from 67, see item 84) — `ConcurrentHashMap.Segment` is STILL IN JDK 21. The "segments were
    removed in Java 8" folklore is wrong twice over.** `static class Segment<K,V> extends
    ReentrantLock implements Serializable` survives at **`ConcurrentHashMap.java:1380`** in JDK 21
    — orchestrator-confirmed by grep, not taken on the writer's report — retained purely for
    **serialization compatibility**, with the same `serialVersionUID` and javadoc as the JDK 8 stub
    at `:1370`. It is a vestigial class that participates in no operation. So the accurate statement
    is that **segment *locking* was abandoned in Java 8 while the `Segment` *class* was kept**, and a
    Java 8+ serialized `ConcurrentHashMap` still writes segment-shaped data. Covered in
    `concurrent-collections/03b-internals-chm-c-bulk-nulls-and-segments.md`. Note also that leaf
    3.14.22's framing is half right: the guard at **:1011** is `if (key == null || value == null)`,
    which bans null **keys as well as values** — most write-ups, and the leaf, phrase it as a values
    ban only.

87. **VERIFIED 2026-08-28 (renumbered from 68, see item 84) — leaf 3.14.33's "`p = 0.25` level distribution" conflates two different
    parameters, and the JDK's own class comment settles it.** The comment at
    **`ConcurrentSkipListMap.java:246-251`** states the hardwired parameters are **`k=1, p=0.5`**,
    and that this means "about **one-quarter** of the nodes have indices. Of those that do, half
    have one level, a quarter have two, and so on (see Pugh's Skip List Cookbook, sec 3.4), up to a
    maximum of **62 levels**". The code at **:660-673** matches exactly: `doPut` first gates whether
    a node is indexed *at all* with `if ((lr & 0x3) == 0)` — a **1-in-4** test — and then grants
    each *additional* level at **1-in-2** odds by shifting a 64-bit random left and testing
    `rnd >= 0L`. So **0.25 is the fraction of nodes that get an index, and 0.5 is the per-level
    continuation probability.** Orchestrator-confirmed against the source, not taken on report.
    Publish both numbers with their distinct meanings; "p = 0.25" alone is wrong.
    Two further confirmations from the same walk: JDK 21 uses `Node<K,V>`/`Index<K,V>` with `head`
    as a plain `Index<K,V>` field and **no `HeadIndex` class**, confirming the post-JDK-12 rewrite —
    every `HeadIndex`-based description is a version trap; and **JEP 491 "Synchronize Virtual
    Threads without Pinning" shipped in JDK 24**, web-confirmed, so leaf 3.14.37's "Java 24+" is
    **correct** — a leaf that survived verification, recorded here so nobody re-checks it.

88. **PROCESS 2026-08-28 (renumbered from 69, see item 84; the 04b half is superseded by item 80, which ACCEPTS 826 and rules against splitting) — two accepted overages and one enforced split in rows 57–61b, recorded
    rather than left silent.** Under item 27 (aim 600, publish to 800 with justification, split
    above 800): `02b-internals-chm-a2-cooperative-resize.md` at **726** and
    `04-copy-on-write.md` at **770** are accepted — both are majority source quotes plus runnable
    proofs, and 02b's two leaves *are* `transfer` plus `helpTransfer`, the two densest leaves in
    §3.14. `03b-internals-chm-c-bulk-nulls-and-segments.md` and `05-blocking-and-lock-free-queues.md`
    both landed at exactly **800**, at the cap. **`04b-build-copy-on-write-by-hand.md` is at 826 —
    26 over the cap — and is an ACCEPTED overage**, on the same reasoning as row 45's
    `04-build-my-tree-map.md` (614): 405 of its lines are four complete compiled classes inside
    fences, splitting a single build-it further would scatter one class across files, which item 27
    explicitly forbids, and a further split for 26 lines was judged worse than a documented
    overage. **Row 61b at 965 was NOT accepted and was split** — see the fold entry.

89. **FIXED 2026-08-28 (renumbered from 70, see item 84) — eight text elements across four of this lane's new SVGs were at 10px,
    below the 11px absolute floor.** Found by the orchestrator's own hygiene sweep, not reported by
    the illustrators: `D-127-spread-and-reserved-sign-bit.svg` (3), `D-136b-ms-queue-cas-next.svg`
    (2), `D-136c-ms-queue-helping-advance.svg` (1), `D-136d-ms-queue-size-traversal.svg` (2). All
    bumped to `font-size="11"` in place with BSD `sed -i ''` (no `.bak` files left behind, since
    `rm` is denied at settings level and a stray `.bak` beside a diagram is its own defect). All 18
    diagrams this lane touched were then re-checked and pass every rule: `viewBox` present, **no**
    fixed `width`/`height`, no font below 11px, no `@import`/`<style>`/external font reference, no
    pure `#000`/`#fff` fill, `role="img"` and `aria-label` present, and **valid XML** under
    `xml.dom.minidom.parse`. **Lesson for future illustrator passes: check the font floor
    mechanically after the pass — the 11px rule is the one an illustrator most often misses**,
    because 10px looks fine on a retina display at authoring size.
    The 18: D-121, D-126, D-127, D-128a–d, D-129, D-130, D-131, D-132, D-133, D-134, D-135,
    D-136a–d.

90. **PROCESS 2026-08-28 (renumbered from 71, see item 84) — the index's own `verify.sh` has a path-check bug that reports every
    diagram embed as broken.** The relative-path check pipes through `tr -d '](' `, which strips the
    brackets but **leaves the trailing `)`**, so every candidate path is tested as
    `…/D-NN-slug.svg)` and fails `[ -f ]`. Reproduced while checking this lane's 17 embeds: all 17
    reported `BROKEN`, all 17 in fact resolve. The correct form is to capture `(\.\./diagrams/[^)]*)`
    and strip both ends, e.g. `sed 's|^(\.\./|<root>/|; s|)$||'`. This compounds the script's already
    documented weakness that four checks set `fail` inside a pipeline subshell and so never change
    the exit code — **read the output, and do not trust a `BROKEN` line from this check without
    re-testing the path by hand.**
