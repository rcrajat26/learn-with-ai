# 21 AI for Coding — namespacing and what a plugin contributes — INTERMEDIATE (§2.5.5–2.5.8)

**Target version: Claude Code v2.1.2xx (August 2026).** | **Part 2 of 6** | [Index](../00-index.md)
Previous: [plugin structure](01-basics-structure.md) · Next: [marketplaces and dependencies](03-marketplaces-and-dependencies.md)

The previous file walked the directory layout and the `.claude-plugin/` trap, and along the way
already showed a complete `plugin.json` for `mvn-test-runner` with `name`, `description`, `version`,
`author`, `homepage`, `repository` and `license` filled in, plus its version-update gotcha: an
installed copy only picks up new behaviour once `version` changes. That is not re-taught here. This
file finishes the manifest's field list with the two fields that example left out, sharpens the
version rule with the two cases it did not yet cover, and then turns to the question the previous
file's "no error, no warning" gotcha raises next: once a plugin *does* load correctly, how does its
content sit next to a project's or a user's own — do they collide, coexist, or does one silently win?

**No diagram of my own in this file** — the dispatch's manifest gives this row no `D-NN`, so the
six-link chain's SVG step is not applicable here throughout; where a diagram already exists for a
mechanism this file leans on, it is cited by id (D-58, D-37, D-43) rather than re-embedded.

## §2.5.5–2.5.6 The rest of `plugin.json`, and how an update actually reaches an install `[DOC]`

**Mental model.** `plugin.json` is not a growing pile of independent settings — it is one manifest
answering three separate questions: *what is this plugin called* (`name`, `description`), *who made
it and where does it live* (`author`, `homepage`, `repository`, `license`), and *how does an install
know when to change* (`version`, `dependencies`, `settings`). The previous file's example answered
the first two groups. This section closes the third.

**Why it exists.** A plugin that could only ever be reinstalled from scratch would be useless for a
team that wants to push a fix without asking everyone to uninstall and reinstall. `version` is the
one field the update mechanism actually reads; `dependencies` and `settings` exist so the manifest
can also declare *what else this plugin needs* and *what it should default to* without a human
reading every file inside it first.

**How it works.** The full field list, `name` through `settings`, with the two the previous file
did not show:

| Field | Required? | Purpose |
|---|---|---|
| `name` | Required | Identifier and skill namespace (`/name:skill`) |
| `description` | Required | Shown in the plugin manager before install |
| `version` | Optional | Gates updates — see below |
| `author` | Optional | Attribution only |
| `homepage` | Optional | Link shown in the plugin manager |
| `repository` | Optional | Source location |
| `license` | Optional | Declared license |
| `dependencies` | Optional | Another plugin (and its marketplace) this one requires — full treatment at §2.5.17 in `plugins/05-cases-and-conversion.md`, not repeated here |
| `settings` | Optional | Default settings inlined in the manifest itself, rather than in a separate `settings.json` file — see the priority rule in §2.5.8 below |

**Gotcha — the two cases the previous file's version rule left open.** The prior file established
"an installed copy updates only when `version` changes." Two specifics sharpen that:

- **A `command` source is the exception.** A plugin distributed as a `command` source is *not*
  gated by `version` the way a marketplace-installed plugin is — it re-runs its source command and
  picks up whatever that command currently returns, on a schedule independent of the manifest's
  `version` field. **Unverified:** the exact refresh trigger for a `command` source is documented on
  the plugin-marketplaces page, which is outside this file's permitted doc set (`settings`,
  `settings-reference`, `permissions`, `hooks`, `sub-agents`, `skills`, `memory`, `plugins`,
  `cli-reference`); recorded in Open questions below.
- **If `version` is omitted entirely**, the version shown to the user comes from "the next source"
  in the manifest's resolution order rather than failing outright — a plugin without an explicit
  `version` is not unversioned, it is version-inferred. **Unverified:** which concrete source that
  fallback is (a git tag, a commit hash, a marketplace-supplied value) is specified on the
  plugins-reference page, also outside the permitted set; recorded in Open questions below.

Both gaps are honestly reported rather than guessed, per this pipeline's rule that a claim outside
the permitted page set gets marked `**Unverified:**` rather than invented.

**Code.** Extending `mvn-test-runner` from the previous file with the two fields this section adds:

```json
{
  "name": "readonly-reviewer",
  "description": "Reviews a diff with read-only tools and blocks on any write- or exec-capable tool call.",
  "version": "2.0.0",
  "author": {
    "name": "IG Group"
  },
  "homepage": "https://github.com/ig-group/readonly-reviewer-plugin",
  "repository": "https://github.com/ig-group/readonly-reviewer-plugin",
  "license": "proprietary",
  "dependencies": [
    {
      "name": "mvn-test-runner",
      "marketplace": "ig-plugins"
    }
  ],
  "settings": {
    "agent": "readonly-reviewer"
  }
}
```

`readonly-reviewer` declares a dependency on `mvn-test-runner` from the `ig-plugins` marketplace —
it wants the test-runner's failing-test summary available before it reviews a diff — and inlines a
`settings` object activating its own `readonly-reviewer` agent as the session default. §2.5.8 below
covers what that `agent` key actually does and why a *separate* `settings.json` file usually carries
it instead of `plugin.json`'s inline form.

**Pitfall:** assuming an unversioned plugin (`version` omitted) means "always installs the very
latest, unpinned" the way an unversioned `npm install` package might feel. What actually happens is
version-inference from a fallback source, not an absence of versioning — the practical effect for a
plugin author is that leaving `version` out does not buy you continuous-deploy semantics, it buys
you an implicit version you do not control by editing `plugin.json`.

> `plugin.json` names, attributes, and versions a plugin; only `version` gates ordinary marketplace
> updates, a `command` source is exempt from that gate, and an omitted `version` falls back to
> another source rather than leaving the plugin unversioned.

## §2.5.7 Namespacing: a plugin's skills always coexist, its agents can be silently overridden `[DOC]` `[TRAP]`

**Mental model.** §1.5.3 already established, and D-37 already drew, that a plugin's skills are
namespaced `/plugin:skill` and therefore *cannot* conflict — two plugins each shipping a skill named
`review` produce `/mvn-test-runner:review` and `/readonly-reviewer:review`, two distinct, permanently
reachable commands. The natural next assumption is that a plugin's **agents** behave the same way.
They do not. An agent's bare name is a single shared namespace across scopes, and when two scopes
define the same bare name, exactly one wins — the other becomes unreachable by that name, full stop.

**Why it exists.** Skills are invoked explicitly by name, so silently letting two same-named skills
both exist causes no ambiguity — the user typed the namespace along with the command. An **agent**,
by contrast, can also be selected implicitly (natural-language mention, or as the session default via
`settings.json`'s `agent` key from §2.5.8), so the harness needs a single deterministic answer to
"which `security-reviewer` did the user mean" rather than two silently-coexisting candidates with the
same bare name.

**When to reach for the override, and when it bites you instead.** Overriding is exactly the
mechanism a team wants when it needs to patch a plugin's agent locally without forking the plugin —
drop a same-named file in `.claude/agents/` and the project's version wins from then on. It bites you
when the override is *accidental*: naming a new project agent the same as an installed plugin's agent
silently shadows the plugin's version everywhere the bare name is used, with no warning at
definition time.

**How it works — the precedence order, highest first:**

| Priority | Location | Scope |
|---|---|---|
| 1 (highest) | Managed settings | Organization-wide |
| 2 | `--agents` CLI flag | Current session |
| 3 | `.claude/agents/` | Current project |
| 4 | `~/.claude/agents/` | All of the user's projects |
| 5 (lowest) | Plugin's `agents/` directory | Wherever the plugin is enabled |

Project beats user, and both beat a plugin's own agent — the exact reverse of the skill-scope order
already drawn at D-43 for §2.1.2, where personal (user) beats project. **Insight:** the two orders
invert because they are solving different problems — the skill order picks which *installed source*
wins when the same skill name is defined at two scopes with no namespace to disambiguate it, while
the agent order exists precisely so a project can patch a plugin's behaviour locally, which only
works if project outranks the very thing being patched.

No new diagram is drawn for this row: D-37 already carries the skill-namespacing picture and D-43
already carries the scope-order picture this table restates for agents; embedding either again here
would duplicate rather than illustrate.

**Code — the override, the scoped @-mention, and the CLI flag.** Say `readonly-reviewer` ships
`agents/security-reviewer.md`, and a project also defines its own `.claude/agents/security-reviewer.md`
with a stricter system prompt. The project's file wins for any bare `@security-reviewer` mention or
natural-language reference to "the security-reviewer agent." The plugin's original is not deleted and
is not merged with the project's — it is simply unreachable by the bare name from here on. It is
still reachable explicitly, scoped:

```text
@agent-readonly-reviewer:security-reviewer look at the auth changes
```

and from the command line, session-wide:

```bash
claude --agent readonly-reviewer:security-reviewer
```

For an agent nested in a plugin subfolder — `agents/review/security.md` inside `readonly-reviewer` —
the scoped identifier folds the subfolder in too: `readonly-reviewer:review:security`, invoked as
`@agent-readonly-reviewer:review:security`.

**Gotcha.** A plugin's own agent definitions are restricted compared to a project's or user's: they
cannot carry `hooks`, `mcpServers`, or `permissionMode` fields — those keys are silently ignored if
present in a plugin's agent file. The only way to give an agent those capabilities is to copy its
definition out of the plugin into `.claude/agents/` or `~/.claude/agents/`, which — because of the
precedence table above — simultaneously promotes it to override the plugin's version. Patching a
plugin agent to add a hook and overriding its name are, mechanically, the same act.

**Pitfall:** the wrong belief is "agents behave like skills — a same-named project agent and plugin
agent just coexist, disambiguated automatically the way `/mvn-test-runner:review` and
`/readonly-reviewer:review` do." The symptom is quieter than the `.claude-plugin/` trap from the
previous file: nothing errors, `/context` shows an agent named `security-reviewer`, and it is only
the *wrong* `security-reviewer` — the project's patched version, when the plugin's original was
actually wanted, or vice versa — with no indication that a second definition exists at all. The fix
is to check the precedence table above before assuming a bare `@`-mention resolves to the plugin's
copy, and to use the fully scoped `plugin:agent` form whenever both versions need to stay reachable
side by side.

**Why people believe it:** skills are the mechanism the reader meets first, and skills genuinely
never collide — generalizing "namespacing prevents conflicts" from skills to agents is a reasonable
one-file-late extrapolation, not a careless one.

> Plugin skills are namespaced into permanently distinct commands and never collide; plugin agents
> share a single bare-name space with project and user agents, and lose it — project, then user,
> then plugin — the moment a name repeats.

## §2.5.8 A plugin's `settings.json`: two keys, nothing else `[DOC]`

A plugin can ship a `settings.json` file at its root — a sibling of `.claude-plugin/`, per the layout
table in the previous file — to apply default configuration the moment the plugin is enabled.
**Mechanism:** as of this target version, only two keys are read from it: `agent`, naming one of the
plugin's own agents to activate as the main thread's persona (its system prompt, tool restrictions and
model all apply session-wide), and `subagentStatusLine`, controlling what a background subagent shows
in the status line while it runs. Every other key in the file is silently ignored — there is no error
for a typo or for a settings key that would be valid in a project's own `settings.json`.

```json
{
  "agent": "readonly-reviewer",
  "subagentStatusLine": "reviewing: {tool_name}"
}
```

Installing `readonly-reviewer` with this file present means the *session itself* opens already
running as the `readonly-reviewer` agent — the plugin has changed the default persona of the whole
conversation, not merely added a skill someone has to remember to invoke.

**Gotcha:** the previous section's `plugin.json` example also carried an inline `"settings": {"agent":
"readonly-reviewer"}` block. When both exist, **`settings.json` wins** — the docs state this
precedence directly: "Settings from `settings.json` take priority over `settings` declared in
`plugin.json`." A plugin author who wants one clearly-visible source of truth should pick one file and
leave the other's `settings` key absent, rather than maintaining the same default in both and
depending on the precedence rule to arbitrate a mismatch.

> A plugin's `settings.json` currently supports exactly two keys, `agent` and `subagentStatusLine`,
> everything else in the file is ignored, and where `plugin.json` also declares inline `settings`,
> the standalone `settings.json` file wins.

## Pitfalls

- **Belief:** "an unversioned plugin (`version` omitted from `plugin.json`) means the install always
  tracks the latest source with no pinning at all." **Surprising outcome:** the version shown and
  gated on is not absent, it is inferred from a fallback source the author does not directly control
  by editing the manifest. **What actually gets the guarantee:** set `version` explicitly if you want
  updates gated on your own release cadence. **Why people believe it:** "optional field, no value
  supplied" reads as "no versioning," the way an unversioned package often does elsewhere.
- **Belief:** "a same-named project agent and a plugin's agent coexist, the same way two plugins'
  same-named skills coexist under different namespaces." **Surprising outcome:** the plugin's agent
  becomes unreachable by its bare name — one wins, silently, per the project > user > plugin
  precedence order, with no error at definition time. **What actually gets the guarantee:** use the
  fully scoped `@agent-plugin:name` form, or `claude --agent plugin:name`, whenever both versions must
  stay reachable. **Why people believe it:** skills — the mechanism introduced first — genuinely never
  collide, and the pattern over-generalizes to agents one file too early.
- **Belief:** "setting `agent` in both `plugin.json`'s inline `settings` and the plugin's
  `settings.json` is harmless redundancy." **Surprising outcome:** if the two ever disagree,
  `settings.json` silently wins with no warning that `plugin.json`'s value was ignored. **What
  actually gets the guarantee:** declare the default agent in exactly one of the two places. **Why
  people believe it:** both fields are named `settings` / `agent` and look like the same declaration
  written twice for convenience, not two sources with a resolution order between them.

## Cheat sheet

| Question | Answer |
|---|---|
| Two `plugin.json` fields with no "Optional" qualifier | `name`, `description` |
| Two optional fields the previous file's example omitted | `dependencies`, `settings` |
| What gates an ordinary marketplace-plugin update | `version` changing in `plugin.json` |
| Exception to the `version` gate | A `command` source |
| `version` omitted entirely | Falls back to another source, not left unversioned |
| Plugin skill conflict | Impossible — always namespaced `/plugin:skill` |
| Plugin agent conflict | Possible — bare name is shared, one definition wins |
| Agent precedence, highest first | Managed settings → `--agents` flag → project → user → plugin |
| Skill scope order (§2.1.2, D-43) for comparison | Enterprise → personal → project, personal beats project |
| Scoped agent mention syntax | `@agent-<plugin>:<name>` (nested: `<plugin>:<folder>:<name>`) |
| Plugin `settings.json` supported keys | `agent`, `subagentStatusLine` — nothing else |
| `plugin.json` inline `settings` vs `settings.json` file | `settings.json` file wins |

## Self-test

1. A plugin ships both a `skills/review/SKILL.md` and an `agents/security-reviewer.md`. Your project
   also defines `.claude/agents/security-reviewer.md`. What happens to each on install?
<details><summary>Answer</summary>
The skill is unaffected — it is namespaced `/plugin-name:review` and never collides with anything.
The agent collides: because project-level (`.claude/agents/`) outranks a plugin's own `agents/`
directory, the project's `security-reviewer.md` wins for any bare mention; the plugin's version
becomes reachable only via the fully scoped `@agent-plugin-name:security-reviewer`.
</details>

2. Why can two plugins each ship a skill called `review` with no conflict, but not two agents called
   `security-reviewer` at project and plugin scope?
<details><summary>Answer</summary>
Skills are always invoked with their namespace baked into the name (`/plugin:skill`), so there is
never a bare, ambiguous form to collide over. Agents can be selected by bare name (mention or default
`agent` setting), so the harness needs a single deterministic winner when two scopes define the same
bare name — hence a precedence order instead of permanent coexistence.
</details>

3. State the agent precedence order from highest to lowest, and name the one scope pair whose
   relative order is the reverse of the equivalent skill-scope order.
<details><summary>Answer</summary>
Managed settings, then the `--agents` CLI flag, then `.claude/agents/` (project), then
`~/.claude/agents/` (user), then a plugin's own `agents/`. Project beats user for agents; for skills
(§2.1.2), personal (user) beats project — the two are inverted.
</details>

4. `plugin.json` declares `"settings": {"agent": "readonly-reviewer"}` and the plugin also ships a
   `settings.json` file with `{"agent": "mvn-test-runner"}`. Which agent activates by default?
<details><summary>Answer</summary>
`mvn-test-runner` — the standalone `settings.json` file's values take priority over `settings`
declared inline in `plugin.json`.
</details>

5. Name the two fields a plugin's `settings.json` supports today, and what happens to a third key
   placed in the same file.
<details><summary>Answer</summary>
`agent` and `subagentStatusLine`. A third key is silently ignored — no error, no warning.
</details>

6. A plugin's `plugin.json` omits `version` entirely. Does the plugin install without a version, and
   does that mean every install always tracks the newest content unpinned?
<details><summary>Answer</summary>
No to both. The version comes from a fallback source rather than being absent, so the plugin is not
literally unversioned; the exact fallback source is outside this file's verified doc set (see Open
questions) but the field is documented as falling back, not disappearing.
</details>

7. You add `hooks` and `mcpServers` fields to a plugin's `agents/security-reviewer.md`. Do they take
   effect?
<details><summary>Answer</summary>
No. Plugin-provided agent definitions silently ignore `hooks`, `mcpServers`, and `permissionMode`.
To use those fields, copy the agent definition into `.claude/agents/` or `~/.claude/agents/`, which
also has the side effect of overriding the plugin's version per the precedence table.
</details>

## Open questions

- **Unverified:** the exact refresh trigger for a `command`-sourced plugin's exemption from the
  `version` gate — documented on the plugin-marketplaces page, outside this file's permitted doc set
  (`settings`, `settings-reference`, `permissions`, `hooks`, `sub-agents`, `skills`, `memory`,
  `plugins`, `cli-reference`).
- **Unverified:** the concrete fallback source used when `plugin.json` omits `version` (git tag,
  commit SHA, or marketplace-supplied value) — documented on the plugins-reference page, also outside
  the permitted set.

---

**Leaves covered:** 2.5.5–2.5.8 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-58 in the previous file draws the layout, D-59 and D-61 in the next two draw marketplaces and the governance lock
**Target version:** Claude Code v2.1.2xx (August 2026)
**Lines:** 342
