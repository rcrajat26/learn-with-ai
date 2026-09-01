# 21 AI for Coding — path rules — BASICS (§1.4.16–1.4.19)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 1 of 6** | [Index](../00-index.md)
Previous: [Bash matching](02-bash-matching.md) · Next: [web, MCP, Agent and Cd rules](04-web-mcp-agent-and-cd-rules.md)

## Files 01 and 02 covered Bash. This file covers the other kind of specifier: a filesystem path.

File 01 established the three-list `deny → ask → allow` pipeline and file 02 walked the Bash
transformation pipeline that runs before a Bash rule ever gets checked. A **path rule** is the second
major specifier shape a permission rule can take — instead of matching command text, it names a file
or directory, using `Read(...)` or `Edit(...)`. This file is one argument in four parts: the syntax a
path rule is written in (§1.4.16), what a `Read` deny propagates to and what it does not (§1.4.17),
which tool names a path rule is ever actually checked against — and which are silently ignored
(§1.4.18), and the outer boundary of the whole mechanism — built-in tools and a fixed set of Bash
commands, never an arbitrary subprocess (§1.4.19). Each leaf narrows what "the permission system
protects this path" can possibly mean, and the answer at the end is smaller than a reader who has
only read §1.4.16 would assume.

## §1.4.16 — `Read`/`Edit` path syntax: gitignore patterns, four anchors

`[ZERO]` A **path rule** is a permission specifier whose parenthesised argument names a file or
directory instead of a command — `Read(./.env)` rather than `Bash(npm test)`. **Gitignore pattern
syntax** is the matching language `.gitignore` files use: a bare name matches at any depth, `*`
matches within one path segment, `**` matches across any number of segments, and a trailing `/**`
matches the directory itself and everything under it. Claude Code reuses this exact syntax for `Read`
and `Edit` rules rather than inventing its own.

`[DOC]` The official documentation states the anchor forms directly:

> Read and Edit rules both use gitignore pattern syntax with four distinct pattern types.

| Pattern | Meaning | Example | Matches |
|---|---|---|---|
| `//path` | Absolute path from filesystem root | `Read(//Users/alice/secrets/**)` | `/Users/alice/secrets/**` |
| `~/path` | Path from home directory | `Read(~/Documents/*.pdf)` | `/Users/alice/Documents/*.pdf` |
| `/path` | Path relative to the settings source | `Edit(/src/**/*.ts)` | `<primary working directory>/src/**/*.ts` in project settings |
| `path` or `./path` | Path relative to current directory | `Read(*.env)` | `<cwd>/*.env` |

— *Configure permissions*, `https://code.claude.com/docs/en/permissions`, re-verified 2026-08-29.

A worked example for each anchor, against a session whose primary working directory is
`/Users/alice/sdlc-harness`:

- **`//abs`** — `Read(//Users/alice/.ssh/id_rsa)` denies exactly one absolute path, regardless of
  which directory the session was launched from or which settings file the rule lives in. This is
  the only anchor that means the same thing everywhere it appears — the same rule text, copied into
  project settings, user settings, or a `--settings` file, always denies the same one file.
- **`~/`** — `Read(~/.aws/credentials)` denies the current user's AWS credentials file no matter what
  project is open. Written once in user settings (`~/.claude/settings.json`), this is the way to block
  a secret file across every project the user ever opens Claude Code in — a bare `/` or bare relative
  rule written in that same user settings file would instead resolve against `~/.claude/`, not against
  whatever project happens to be open, so it would not achieve the same cross-project reach (see the
  next example for exactly why).
- **`/`** — `Edit(/src/**/*.ts)` written in `.claude/settings.json` at a project's root resolves to
  `<primary working directory>/src/**/*.ts` — the project's own `src/` tree. The identical literal
  rule, written instead in `~/.claude/settings.json`, resolves to `~/.claude/src/**/*.ts` — a
  directory that almost certainly does not exist on disk — because a `/`-anchored rule resolves
  against the directory associated with **the settings file that defines it**, not against whatever
  project the session happens to be open in at the time.
- **bare / `./`** — `Read(./.env)` and `Read(./secrets/**)` are the documentation's own paste-ready
  examples for excluding sensitive files, and both anchor at the session's current directory:
  `Read(./.env)` denies `<cwd>/.env` specifically, and `Read(./secrets/**)` denies the whole
  `<cwd>/secrets/` directory and everything nested under it, however deep.

Bare filenames follow gitignore depth semantics regardless of which anchor style is used —
`Read(.env)` and `Read(**/.env)` are documented as equivalent, both blocking any `.env` at or under
the current directory, but neither blocking a `.env` that lives in a parent directory or in a
completely separate sibling project. A single-segment directory pattern such as `Read(secrets/**)`
additionally matches a `secrets` directory **at any depth** under the current directory when the rule
is written as `deny` or `ask` — for an `allow` rule, the identical pattern text matches only the
top-level `<cwd>/secrets`, and nothing nested deeper. This asymmetry is deliberate, not an
inconsistency: an allow rule that only reached the top level cannot accidentally permit a `secrets/`
directory an author never even knew a dependency had copied three levels deep into `vendor/`, while a
deny or ask rule reaching every depth cannot be dodged simply by nesting the sensitive directory
somewhere else in the tree where a narrower rule would have missed it.

**Insight:** the four anchors are not stylistic alternatives to the same target — `//`, `~/`, and `/`
each resolve against a **different root** (the filesystem root, the home directory, and the location
of the settings file that defines the rule, respectively), so identical pattern text produces three
different denied paths depending only on which anchor prefix was chosen. Picking the wrong anchor for
a rule meant to be shared (writing `/secrets/**` in user settings, meaning "every project's secrets,"
when it actually resolves to `~/.claude/secrets/**`) is a **silent no-op** — it parses, it loads, and
it denies a path that was never the intended target, with nothing in the settings file itself to flag
the mismatch.

## §1.4.17 — a `Read` deny also blocks `Edit` and `Write`, but not `NotebookEdit`

`[DOC]` `[VERSION]` The documentation states the coverage and the version gate together:

> A `Read` deny rule also blocks the Edit and Write tools on the same path, including creating a new
> file there. NotebookEdit isn't covered, so add an `Edit` deny rule for paths no tool may change.
> The check requires Claude Code v2.1.208 or later on edits, and v2.1.228 or later on writes.

— *Configure permissions*, re-verified 2026-08-29.

**On Claude Code v2.1.2xx (the target version for this guide), both halves of that check are
active** — edits have been covered since v2.1.208 and writes since v2.1.228, both well before the
current release line. A reader running an older binary between those two version numbers would find
that a `Read` deny already blocked `Edit` at the same path, while a brand-new file created via `Write`
at that same path still succeeded — the version trap to carry forward if this claim is ever repeated
about an older build, or read off an old screenshot with no version banner attached.

Concretely, with only this rule in place:

```json
{
  "permissions": {
    "deny": [
      "Read(./secrets/**)"
    ]
  }
}
```

on v2.1.2xx: `Read`, `Edit`, and `Write` on a file under `secrets/` are all blocked — the `Write` case
includes creating a brand-new file there for the first time, not only editing one that already
exists — but `NotebookEdit` on a `.ipynb` file under `secrets/` **succeeds**, because `NotebookEdit`
is not one of the tools a `Read` deny propagates to. The fix stated directly in the quote is to add a
second, explicit rule:

```json
{
  "permissions": {
    "deny": [
      "Read(./secrets/**)",
      "Edit(./secrets/**)"
    ]
  }
}
```

Adding the `Edit` deny does not close the `NotebookEdit` gap on its own — see §1.4.18: `Edit(path)` is
one of only two rule forms ever consulted for file permissions, and a `NotebookEdit(...)` path rule is
never consulted regardless of how carefully it is written. There is no single rule shape that blocks
notebook edits by path at all; the only lever available is a bare tool-name deny,
`"deny": ["NotebookEdit"]`, which removes the tool from Claude's context entirely — for every path,
project-wide — rather than scoping the block to one sensitive directory.

**Pitfall:** the wrong belief is "I denied `Read` on the secrets folder, so nothing can touch it
there." The symptom is a notebook file under that same folder getting edited anyway, with no warning
at the time the `Read` deny rule was originally written — the rule silently covers three tools
(`Read`, `Edit`, `Write`) and just as silently omits a fourth (`NotebookEdit`), and nothing in the
settings file or its loading distinguishes the covered set from the omitted one. The fix is to name
every tool the leaf actually needs blocked, explicitly: a `Read` deny for read access, an `Edit` deny
for edit/write access (both propagate as described above), and, if notebooks fall inside the same
sensitive scope, a separate bare `NotebookEdit` deny on top. **Why people believe it:** `Read` deny
propagating to `Edit` and `Write` at all already reads as generous, "obviously correct" behaviour —
the natural next assumption is that the propagation is complete, when in fact it is exactly one tool
short of complete, and that one tool is easy to forget because it is the least commonly used of the
four.

## §1.4.18 — file permissions are checked against `Edit(path)` and `Read(path)` only

`[TRAP]` `[DOC]` `[VERSION]` This is the single most dangerous silently-ignored configuration in the
whole permission system, because the settings file that gets it wrong reads exactly as though the
restriction exists — there is no syntax error, no red flag at a casual glance, nothing to distinguish
it from a rule that actually works. The documentation is explicit and names every tool the mistake is
commonly made with:

> Claude Code checks file permissions against `Edit(path)` and `Read(path)` rules only. If you write
> a path rule for `Write`, `NotebookEdit`, `Glob`, or the legacy `MultiEdit` tool instead, Claude Code
> accepts the rule but never consults it, and warns at startup, except for a `Glob` rule passed in
> `--allowedTools`. Use `Edit(docs/**)` in place of `Write(docs/**)`, `NotebookEdit(docs/**)`, or
> `MultiEdit(docs/**)`, and `Read(docs/**)` in place of `Glob(docs/**)`. Claude Code doesn't warn
> about a tool-name rule with no path, such as a deny rule for `Write`; it matches that rule at the
> tool level everywhere. **Requires Claude Code v2.1.210 or later.**

— *Configure permissions*, re-verified 2026-08-29.

`[VERSION]` The startup warning itself — the one safety net that would catch this exact mistake
before it ever bites in production — is only present from **v2.1.210 onward**. A settings file with a
`Write(docs/**)` path rule, loaded by a binary older than v2.1.210, produces no warning whatsoever:
the rule is silently accepted and just as silently never consulted, with no signal at load time that
anything at all is wrong. On the v2.1.2xx target version of this guide the warning does fire, which is
the behaviour every example below assumes — but a reader troubleshooting against an older install, or
reading an old blog post's screenshot that shows no warning banner, should not conclude from its
absence that the rule ever actually worked; the rule silently doing nothing predates the warning by a
wide margin.

Here is the settings object that looks like it protects `docs/` from being written, and does not:

```json
{
  "permissions": {
    "deny": [
      "Write(docs/**)"
    ]
  }
}
```

Nothing about this JSON is malformed. It parses cleanly. It loads without complaint on any version.
Claude Code accepts `Write(docs/**)` as a syntactically valid deny-list entry — and then never checks
a single `Write` call against it, because `Write` calls are not gated by path rules at all; only
`Edit(path)` and `Read(path)` are ever consulted for file-permission purposes, full stop. Every write
into `docs/` proceeds exactly as if this deny rule had never been written in the first place. The
corrected settings object, using the rule form Claude Code actually checks:

```json
{
  "permissions": {
    "deny": [
      "Edit(docs/**)"
    ]
  }
}
```

`Edit(docs/**)` blocks the built-in tools that edit files — which, per §1.4.17, already includes
`Write` on this target version — so this single `Edit` deny does everything the author of the first
JSON block believed `Write(docs/**)` already did.

| Rule form the author writes | What Claude Code does with it |
|---|---|
| `Write(docs/**)` | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ |
| `NotebookEdit(docs/**)` | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ |
| `MultiEdit(docs/**)` | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ (legacy tool) |
| `Glob(docs/**)` in a settings file | accepted, parsed, **never consulted** — warns at startup on v2.1.210+ |
| `Glob(docs/**)` passed via `--allowedTools` | the one documented exception — **is** consulted |
| `Write` (bare, no path) | matched at the tool level everywhere — **no warning, because there is nothing wrong**: a bare tool-name deny removes the whole tool from context |
| `Edit(docs/**)` | the correct form — **is** consulted |
| `Read(docs/**)` | the correct form for read-gating — **is** consulted |

**Pitfall:** the wrong belief is "I wrote a `Write` path rule, so writes to this path are blocked."
The symptom: the deny rule sits in the settings file, reads as fully intentional to any reviewer, and
produces at most a startup-log warning most workflows never look at — and every `Write` call to the
path proceeds unblocked regardless, with no runtime error and no denial message to hint that anything
failed to take effect. The fix is entirely mechanical: any path-scoped file-permission rule is written
as `Edit(...)` or `Read(...)`, never as `Write(...)`, `NotebookEdit(...)`, `MultiEdit(...)`, or
`Glob(...)` inside a settings file (the sole exception being `Glob` passed through `--allowedTools`,
which is consulted). **Why people believe it:** the tool names line up too well for the mistake to
feel like a mistake — `Write` sounds exactly like the tool that should own a "block writes here" rule,
and the settings schema accepts the string with zero complaint at write time, so nothing in the
day-to-day authoring loop ever contradicts the belief.

**Interview:** "You wrote `Write(docs/**)` in `deny` and writes to `docs/` still happen. Why?" — file
permissions are checked against `Edit(path)` and `Read(path)` only; every other tool name accepted in
a path rule (`Write`, `NotebookEdit`, `MultiEdit`, and `Glob` inside a settings file) is parsed and
silently never consulted. Use `Edit(docs/**)` instead, which — since a `Read`/`Edit` deny already
propagates to `Write` per §1.4.17 on this target version — blocks the write too, in one rule.

**D-32** — Which tools consult path rules.

| Tool | Path rule consulted? | Silently accepted and ignored? | Write instead | Stops it at OS level |
|---|---|---|---|---|
| `Read` | Yes | — | — | sandbox filesystem restriction |
| `Edit` | Yes | — | — | sandbox filesystem restriction |
| `Write` | No | Yes (warns on v2.1.210+) | `Edit(path)` | sandbox filesystem restriction |
| `NotebookEdit` | No | Yes (warns on v2.1.210+) | `Edit(path)` — but per §1.4.17, still needs an *explicit* `Edit` deny, since a `Read` deny alone does not propagate to `NotebookEdit` either | sandbox filesystem restriction |
| `MultiEdit` (legacy) | No | Yes (warns on v2.1.210+) | `Edit(path)` | sandbox filesystem restriction |
| `Glob` | No, in a settings file | Yes (warns on v2.1.210+) — **except** when passed via `--allowedTools`, which *is* consulted | `Read(path)` | sandbox filesystem restriction |
| `Grep` | Path rules do not gate it directly; Claude Code makes a **best-effort attempt** to apply `Read` rules to it | not a silently-ignored form — it is a best-effort extension of `Read`, not a separate rule shape | — | sandbox filesystem restriction |
| Bash file commands (`cat`, `head`, `tail`, `sed`) | Yes — `Read`/`Edit` deny rules are recognised against these specific Bash forms | — | — | sandbox blocks the underlying process, not the rule |
| An arbitrary subprocess (e.g. a Python script opening the file itself) | **No** — not reached by any permission rule | not applicable — there is no rule form for this at all | nothing in the permission system reaches it | **the sandbox is the only answer** — see §1.4.19 |

## §1.4.19 — the boundary: built-in tools and recognised Bash commands, not an arbitrary subprocess

`[TRAP]` `[DOC]` §1.4.17 and §1.4.18 both describe what a `Read`/`Edit` deny rule *does* cover. This
leaf states the outer boundary of what it covers at all — the point past which no permission rule of
any shape reaches, and only the sandbox does.

> Read and Edit deny rules apply to Claude's built-in file tools and to file commands Claude Code
> recognizes in Bash, such as `cat`, `head`, `tail`, and `sed`. They don't apply to arbitrary
> subprocesses that read or write files indirectly, like a Python or Node script that opens files
> itself. For OS-level enforcement that blocks all processes from accessing a path, enable the
> sandbox.

— *Configure permissions*, re-verified 2026-08-29.

So the same `Read(./secrets/**)` deny rule that stops the built-in `Read` tool, and stops
`cat ./secrets/token.txt` run through the `Bash` tool, does **nothing at all** to:

```python
python3 -c "print(open('./secrets/token.txt').read())"
```

if that one-liner is itself launched through `Bash`. Claude Code's Bash-side recognition of `cat`,
`head`, `tail`, and `sed` (and their siblings) is a **named-command allowlist for enforcement
purposes**, not a general "detect any file access inside a subprocess" mechanism — a script that opens
a file handle in its own interpreter, rather than invoking a recognised command name, is invisible to
the permission layer entirely, because the permission layer never inspects what a running process does
internally, only which command name Claude Code chose to launch.

The three leaves in this file are one argument, restated here as a single chain: a `Read` deny covers
`Edit` and `Write` but not `NotebookEdit` (§1.4.17); the only rule forms ever consulted for file access
are `Edit(path)` and `Read(path)`, so a rule written against any other tool name is a no-op (§1.4.18);
and even a correctly-written `Read`/`Edit` deny only reaches the built-in tools and a fixed set of
recognised Bash commands, never an arbitrary subprocess that reads the file through its own code
(§1.4.19). Each leaf narrows what "the permission system protects this path" can possibly mean, and
the answer at the end of the chain is: **less** than a reader who has only read §1.4.16 would assume.

**Pitfall:** the wrong belief is "a `Read` deny is a filesystem-level guarantee — nothing running
inside this session can read that path, full stop." The symptom is a `python3`, `node`, or any other
interpreter invocation, run through the `Bash` tool, reading a denied path successfully and returning
its contents straight into the conversation, with the permission system never even consulted because
the file access never went through a recognised command name or a built-in tool in the first place.
The fix is **enable the sandbox** for OS-level enforcement that blocks every process — recognised or
not, named or not — from reaching the path at all, rather than relying on the permission layer to
police subprocess internals it structurally cannot see. **Why people believe it:** the permission
system's own language ("deny", "blocked") reads like an absolute security boundary, and for the
built-in tools and the recognised Bash commands, it genuinely is one — the gap only becomes visible
once a subprocess does its own file I/O instead of shelling out to a name Claude Code happens to
recognise.

## Pitfalls

- **Belief:** "I denied `Read` on the secrets folder, so nothing can touch anything under it."
  **Outcome:** a `NotebookEdit` call against a file under that folder still succeeds, because a `Read`
  deny propagates to `Edit` and `Write` but not to `NotebookEdit`. **Fix:** add an explicit `Edit`
  deny for the same path, and a bare `NotebookEdit` deny if notebooks are in scope at all. **Why
  people believe it:** the propagation to `Edit`/`Write` already looks generous, so completeness is
  the natural — and wrong — next assumption.
- **Belief:** "I wrote `Write(docs/**)` in `deny`, so writes to `docs/` are blocked." **Outcome:**
  Claude Code accepts and parses the rule, then never consults it — file permissions are checked
  against `Edit(path)` and `Read(path)` only, so every `Write` proceeds unblocked (with a startup
  warning on v2.1.210+ that most workflows never read). **Fix:** write `Edit(docs/**)` instead, which
  is a consulted form and, on this target version, already propagates to `Write` per §1.4.17. **Why
  people believe it:** the tool name `Write` matches the intent so exactly that the settings schema
  accepting the string with no load-time error reads as confirmation it works.
- **Belief:** "A `Read` deny on a path is a filesystem-level guarantee that nothing in this session
  can read it." **Outcome:** a `python3 -c "open(...).read()"` one-liner run through `Bash` reads the
  denied path successfully, because Read/Edit deny rules only cover built-in file tools and the
  specific Bash commands Claude Code recognises (`cat`, `head`, `tail`, `sed`), not an arbitrary
  subprocess doing its own file I/O. **Fix:** enable the sandbox for OS-level enforcement that blocks
  every process, recognised or not. **Why people believe it:** the word "deny" reads as an absolute
  security boundary, and for the tools it actually covers, it is one.

## Cheat sheet

| Fact | Value |
|---|---|
| Read/Edit path syntax | gitignore pattern syntax |
| Four anchors | `//path` (filesystem root), `~/path` (home), `/path` (settings-source-relative), `path`/`./path` (cwd-relative) |
| `Read(./.env)`, `Read(./secrets/**)` | documentation's own paste-ready sensitive-file examples |
| Bare filename depth | `Read(.env)` = `Read(**/.env)`, matches at any depth under cwd |
| Single-segment dir pattern, allow vs deny/ask | allow: top level only; deny/ask: any depth |
| Read deny propagates to | `Edit`, `Write` (not `NotebookEdit`) |
| Version gate on that propagation | edits: v2.1.208+; writes: v2.1.228+ |
| File permissions consulted for | `Edit(path)`, `Read(path)` — only |
| Path rules accepted but never consulted | `Write(...)`, `NotebookEdit(...)`, `MultiEdit(...)`, `Glob(...)` in settings (except `Glob` via `--allowedTools`) |
| Startup warning for ignored path rule | v2.1.210+ |
| Bare tool-name deny (no path) | matched at tool level everywhere — no warning, nothing wrong |
| Read/Edit deny reaches | built-in file tools, recognised Bash commands (`cat`, `head`, `tail`, `sed`, …) |
| Read/Edit deny does NOT reach | an arbitrary subprocess reading the file itself (e.g. a Python script) |
| OS-level fix for that gap | enable the sandbox |

## Self-test

<details><summary>1. Why does `Read(~/secrets/**)` written in user settings not block a `secrets/` directory inside a project?</summary>
`~/` anchors at the home directory regardless of which project is open, so the rule denies
`~/secrets/**` specifically — a project's own `secrets/` directory, sitting under the project root
rather than under the home directory, is a completely different path and is untouched by this rule.
</details>

<details><summary>2. `Edit(/src/**/*.ts)` is written once and copied verbatim into a project's `.claude/settings.json` and then into `~/.claude/settings.json`. Does it protect the same directory in both places?</summary>
No. A `/`-anchored rule resolves against the directory associated with the settings file that defines
it. In the project's own settings it resolves to `<primary working directory>/src/**/*.ts`. Copied
into user settings, it instead resolves to `~/.claude/src/**/*.ts` — a directory that almost certainly
does not exist — because the anchor is the settings-file location, not the project currently open.
</details>

<details><summary>3. A settings file denies `Read(./secrets/**)` only. Does a `Write` into a brand-new file under `secrets/` succeed? Does a `NotebookEdit` there succeed?</summary>
Neither creating a new file with `Write` nor editing an existing one with `Edit` succeeds — a `Read`
deny propagates to both, on v2.1.208+/v2.1.228+. `NotebookEdit`, however, is explicitly not covered
by that propagation, so a `NotebookEdit` call against a file under `secrets/` succeeds unless a
separate `Edit` (or bare `NotebookEdit`) deny is added.
</details>

<details><summary>4. A project denies `Write(docs/**)`. Does this block writes into `docs/`? What is the correct rule?</summary>
No. File permissions are checked against `Edit(path)` and `Read(path)` rules only; a `Write` path
rule is accepted and parsed but never consulted (Claude Code warns at startup on v2.1.210+, but the
rule itself still does nothing). The correct rule is `Edit(docs/**)`.
</details>

<details><summary>5. Why doesn't a bare `"deny": ["Write"]` rule get the same startup warning that `"deny": ["Write(docs/**)"]` gets?</summary>
There is nothing wrong with the bare form — a tool-name rule with no path matches at the tool level
everywhere, which is exactly how Claude Code checks it. The warning exists only for the path-scoped
form, because that is the form silently never consulted; the bare form was never claiming to be
path-scoped in the first place.
</details>

<details><summary>6. `Read(./secrets/**)` and `Edit(./secrets/**)` are both denied. Does a Bash-tool invocation of `cat ./secrets/token.txt` succeed? Does `python3 -c "print(open('./secrets/token.txt').read())"` run through Bash succeed?</summary>
`cat` is one of the Bash commands Claude Code recognises for Read/Edit deny enforcement, so it is
blocked. The Python one-liner is not — Read/Edit deny rules cover built-in tools and recognised Bash
commands, not an arbitrary subprocess doing its own file I/O, so it succeeds. Only the sandbox blocks
that case.
</details>

<details><summary>7. State the single chain that §1.4.17–1.4.19 build together.</summary>
A `Read` deny covers `Edit` and `Write` but not `NotebookEdit` (§1.4.17); the only rule forms ever
consulted for file access are `Edit(path)` and `Read(path)`, so a rule against any other tool name is
a no-op (§1.4.18); and even a correct `Read`/`Edit` deny only reaches built-in tools and a fixed set
of recognised Bash commands, never an arbitrary subprocess (§1.4.19). Each leaf narrows what "this
path is protected" can mean.
</details>

<details><summary>8. Why is the allow/deny asymmetry for single-segment directory patterns like `secrets/**` deliberate rather than a bug?</summary>
An allow rule reaching every depth could accidentally permit a `secrets/` directory copied three
levels deep by a dependency the author never audited. A deny/ask rule reaching only the top level
could be dodged by nesting the sensitive directory somewhere else in the tree. Allow matching only the
top level and deny/ask matching every depth closes both holes at once.
</details>

## Open questions

None.

---

**Leaves covered:** 1.4.16–1.4.19 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-32
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 414
