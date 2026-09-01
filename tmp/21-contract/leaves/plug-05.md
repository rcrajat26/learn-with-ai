### §2.5 Plugins and marketplaces

2.5.16 `[CASE]` The harness's `marketplace.json`: `allowCrossMarketplaceDependenciesOn:
       ["ig-superclaude"]` and a description that explains *why* the pivot to a standalone
       marketplace happened, citing its own RFC. Documentation living in the config. `[CASE]`
2.5.17 `[CASE]` Its `plugin.json`: `version: 0.10.2`, proprietary licence,
       `dependencies: [{ name: "ig-superclaude", marketplace: "ig-superclaude" }]`. `[CASE]`
2.5.18 `[TRAP]` `${CLAUDE_PLUGIN_ROOT}` is the plugin's **install/cache** directory, not the repo.
       A hook ported from `<repo>/.claude/hooks/` cannot keep resolving the repo root as
       `dirname "$0"/../..`. Path assumptions are the number-one porting bug. `[TRAP]` `[CASE]`
2.5.19 `[CASE]` The harness's fix and its discipline: resolve `HARNESS_ROOT` → `git rev-parse
       --show-toplevel`, and **refuse with a clear message** rather than inventing a third
       fallback. Quote the header comment that says exactly that. `[CASE]`
2.5.20 `[BUILD]` Convert a `.claude/` folder into a plugin: manifest, move the components, migrate
       settings hooks into `hooks/hooks.json`, test with `--plugin-dir`, `claude plugin validate`,
       then delete the originals so the plugin copies actually take effect. `[BUILD]`



